import json
import traceback
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import (
    QMenu,
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from model import PowerNet, engineer_features, get_feature_names, TARGET_CONFIGS


def resource_path(relative_path: str) -> Path:
    return Path(__file__).resolve().parent / relative_path


class DataFrameModel(QAbstractTableModel):
    def __init__(self, dataframe: pd.DataFrame):
        super().__init__()
        self._dataframe = dataframe.copy()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._dataframe)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.TextAlignmentRole):
            return None

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter | Qt.AlignVCenter

        value = self._dataframe.iat[index.row(), index.column()]
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._dataframe.columns[section])
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled


class FileDropZone(QLabel):
    fileDropped = Signal(str)

    def __init__(self, text: str):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setObjectName("dropZone")
        self.setMinimumHeight(160)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                self.fileDropped.emit(file_path)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()


class PredictionWindow(QMainWindow):
    SUPPORTED_EXTENSIONS = {".json", ".csv", ".xlsx"}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital IC Power Prediction")
        self.setMinimumSize(1100, 720)
        self._dataframe = None
        self._current_file_path = None

        # One cached (model, input_dim) pair per target column, e.g.
        # {"total_power_uW": (model, input_dim), "dynamic_power_uW": ...}.
        self._models = {}
        self._preprocessor = None

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self._build_ui()
        self._apply_style()

    def _build_menu_bar_(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        export_menu = QMenu("Export as...", self)
        file_menu.addMenu(export_menu)

        self._export_csv_action = export_menu.addAction("CSV (.csv)")
        self._export_csv_action.triggered.connect(lambda : self._export_results("csv"))

        self._export_json_action = export_menu.addAction("JSON (.json)")
        self._export_json_action.triggered.connect(lambda: self._export_results("json"))

        self._export_xlsx_action = export_menu.addAction("XLSX (.xlsx)")
        self._export_xlsx_action.triggered.connect(lambda: self._export_results("xlsx"))

        self._set_export_actions_enabled(False)

    def _set_export_actions_enabled(self, enabled : bool):
        self._export_csv_action.setEnabled(enabled)
        self._export_json_action.setEnabled(enabled)
        self._export_xlsx_action.setEnabled(enabled)
        self._copy_button.setEnabled(enabled)

    def _export_results(self, fmt: str):
        if self._dataframe is None:
            QMessageBox.warning(self, "Nothing to Export", "Load a file and run a prediction first.")
            return

        prediction_columns = [
            "predicted_total_power_uW",
            "predicted_dynamic_power_uW",
            "predicted_leakage_power_uW",
        ]
        if not all(col in self._dataframe.columns for col in prediction_columns):
            QMessageBox.warning(
                self, "Nothing to Export", "Run Predict Power first, then export."
            )
            return

        features, _, _ = get_feature_names()
        input_columns = [col for col in features if col in self._dataframe.columns]
        export_columns = input_columns + prediction_columns
        export_df = self._dataframe[export_columns]

        filters = {
            "csv": "CSV Files (*.csv)",
            "json": "JSON Files (*.json)",
            "xlsx": "Excel Files (*.xlsx)",
        }
        default_name = f"predicted_power.{fmt}"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Predictions", default_name, filters[fmt]
        )
        if not file_path:
            return

        try:
            if fmt == "csv":
                export_df.to_csv(file_path, index=False)
            elif fmt == "json":
                export_df.to_json(file_path, orient="records", indent=2)
            else:
                export_df.to_excel(file_path, index=False)
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(self, "Export Error", str(exc))
            return

        self._status_label.setText(f"Exported {len(export_df)} row(s) to {Path(file_path).name}.")

    def _copy_results(self):
        if self._dataframe is None:
            return

        prediction_columns = [
            "predicted_dynamic_power_uW",
            "predicted_leakage_power_uW",
            "predicted_total_power_uW",
        ]

        if not all(col in self._dataframe.columns for col in prediction_columns):
            QMessageBox.warning(
                self, "Nothing to Copy", "Run Predict Power first, then copy."
            )
            return

        if len(self._dataframe) == 1:
            row = self._dataframe.iloc[0]
            text = (
            f"Predicted Dynamic: {row['predicted_dynamic_power_uW']:.4f} µW\n"
            f"Predicted Leakage: {row['predicted_leakage_power_uW']:.4f} µW\n"
            f"Predicted Total: {row['predicted_total_power_uW']:.4f} µW"
        )
        else:
            export_df = self._dataframe[prediction_columns]
            text = export_df.to_csv(sep="\t", index=False)

        QApplication.clipboard().setText(text)
        self._status_label.setText("Predicted power values copied to clipboard.")


    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        self._copy_button = QPushButton("Copy Result")
        self._copy_button.setEnabled(False)
        self._copy_button.clicked.connect(self._copy_results)
        self._copy_button.setObjectName("copyButton")
        self._copy_button.setToolTip("Copy predicted power values to clipboard.")
        self._copy_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_menu_bar_()

        title_label = QLabel("Digital IC Power Prediction")
        title_label.setObjectName("titleLabel")
        subtitle_label = QLabel(
            "Load a JSON, CSV, or XLSX file and predict IC power in µW with a modern desktop interface."
        )
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setWordWrap(True)

        self._drop_zone = FileDropZone(
            "Drag and drop a .json, .csv or .xlsx file here\nor click Browse File to select a dataset."
        )
        self._drop_zone.fileDropped.connect(self._on_file_selected)

        self._file_name_label = QLabel("No file attached.")
        self._file_name_label.setObjectName("fileNameLabel")
        self._file_name_label.setWordWrap(True)

        browse_button = QPushButton("Browse File")
        browse_button.clicked.connect(self._browse_file)
        browse_button.setObjectName("browseButton")
        browse_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._predict_button = QPushButton("Predict Power")
        self._predict_button.setEnabled(False)
        self._predict_button.clicked.connect(self._predict_power)
        self._predict_button.setObjectName("predictButton")
        self._predict_button.setToolTip("Predict Dynamic, Leakage and Total power.")
        self._predict_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._reset_button = QPushButton("Reset")
        self._reset_button.setEnabled(False)
        self._reset_button.clicked.connect(self._reset)
        self._reset_button.setObjectName("resetButton")
        self._reset_button.setToolTip("Clear the loaded file.")
        self._reset_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._status_label = QLabel("No file loaded.")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setWordWrap(True)

        self._result_label = QLabel("Awaiting input file to run prediction.")
        self._result_label.setObjectName("resultLabel")
        self._result_label.setWordWrap(True)

        self._input_table = QTableView()
        self._input_table.setObjectName("inputTable")
        self._input_table.horizontalHeader().setStretchLastSection(True)
        self._input_table.verticalHeader().setVisible(False)
        self._input_table.setSelectionBehavior(QTableView.SelectRows)
        self._input_table.setEditTriggers(QTableView.NoEditTriggers)
        self._input_table.setAlternatingRowColors(True)

        self._prediction_table = QTableView()
        self._prediction_table.setObjectName("predictionTable")
        self._prediction_table.horizontalHeader().setStretchLastSection(True)
        self._prediction_table.verticalHeader().setVisible(False)
        self._prediction_table.setSelectionBehavior(QTableView.SelectRows)
        self._prediction_table.setEditTriggers(QTableView.NoEditTriggers)
        self._prediction_table.setAlternatingRowColors(True)

        preview_splitter = QSplitter(Qt.Horizontal)
        preview_splitter.addWidget(self._boxed_widget(f"Input Data Preview:", self._input_table))
        preview_splitter.addWidget(self._boxed_widget("Predicted Power", self._prediction_table))
        preview_splitter.setSizes([650, 350])

        left_panel = QVBoxLayout()
        left_panel.addWidget(title_label)
        left_panel.addWidget(subtitle_label)
        left_panel.addSpacing(-5)
        left_panel.addWidget(self._drop_zone)
        left_panel.addWidget(self._file_name_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(browse_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self._reset_button)
        buttons_layout.addWidget(self._copy_button)
        buttons_layout.addWidget(self._predict_button)
        left_panel.addLayout(buttons_layout)
        left_panel.addSpacing(8)
        left_panel.addWidget(self._status_label)
        left_panel.addWidget(self._result_label)
        left_panel.addStretch(1)

        main_layout = QVBoxLayout(central)
        main_layout.addLayout(left_panel)
        main_layout.addSpacing(16)
        main_layout.addWidget(preview_splitter)

    def _boxed_widget(self, title: str, inner_widget: QWidget) -> QWidget:
        box = QWidget()
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(12, 12, 12, 12)
        box_layout.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("boxHeading")
        box_layout.addWidget(heading)
        box_layout.addWidget(inner_widget)
        box.setObjectName("boxFrame")
        box.setMinimumHeight(360)
        return box

    def _apply_style(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#121212"))
        palette.setColor(QPalette.WindowText, QColor("#EEEEEE"))
        palette.setColor(QPalette.Base, QColor("#1E1E1E"))
        palette.setColor(QPalette.AlternateBase, QColor("#242424"))
        palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
        palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
        palette.setColor(QPalette.Text, QColor("#EEEEEE"))
        palette.setColor(QPalette.Button, QColor("#1E1E1E"))
        palette.setColor(QPalette.ButtonText, QColor("#EEEEEE"))
        palette.setColor(QPalette.Highlight, QColor("#3A8DFF"))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        QApplication.instance().setPalette(palette)

        self.setStyleSheet(
            """
            QMainWindow { background: #121212; }
            QLabel#titleLabel { font-size: 26px; font-weight: 700; color: #FFFFFF; }
            QLabel#subtitleLabel { color: #CCCCCC; font-size: 14px; }
            QLabel#statusLabel, QLabel#resultLabel { font-size: 13px; color: #DDDDDD; }
            QLabel#fileNameLabel { font-size: 13px; font-weight: 600; color: #3A8DFF; padding: 4px 2px; }
            QLabel#resultLabel { font-weight: 600; }
            QLabel#boxHeading { font-size: 15px; font-weight: 700; color: #FFFFFF; }
            QLabel#dropZone { border: 2px dashed #4A90E2; border-radius: 14px; padding: 24px; color: #AAAAAA; background: #191919; }
            QPushButton { border: none; border-radius: 12px; padding: 12px 20px; font-size: 14px; }
            QPushButton#browseButton { background: #2F80ED; color: #FFFFFF; }
            QPushButton#browseButton:hover { background: #4A90FF; }
            QPushButton#predictButton { background: #12B886; color: #FFFFFF; }
            QPushButton#predictButton:disabled { background: #444444; color: #888888; }
            QPushButton#predictButton:hover:enabled { background: #1CD88C; }
            QPushButton#resetButton { background: transparent; color: #DDDDDD; border: 1px solid #444444; }
            QPushButton#resetButton:hover:enabled { background: #2A2A2A; border-color: #666666; }
            QPushButton#resetButton:disabled { color: #555555; border-color: #2E2E2E; }
            QPushButton#copyButton { background: transparent; color: #DDDDDD; border: 1px solid #444444; }
            QPushButton#copyButton:hover:enabled { background: #2A2A2A; border-color: #666666; }
            QPushButton#copyButton:disabled { color: #555555; border-color: #2E2E2E; }
            QWidget#boxFrame { background: #191919; border: 1px solid #2E2E2E; border-radius: 16px; }
            QTableView { background: #141414; border: 1px solid #2E2E2E; gridline-color: #2E2E2E; color: #EEEEEE; }
            QHeaderView::section { background: #1F1F1F; color: #EEEEEE; padding: 6px; border: none; }
            QTableView::item { padding: 6px; }
            QTableView::item:selected { background: #3A6ED8; color: #FFFFFF; }
            """
        )

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open data file",
            str(Path(__file__).resolve().parent),
            "Data Files (*.json *.csv *.xlsx)",
        )
        if file_path:
            self._on_file_selected(file_path)

    def _on_file_selected(self, path: str):
        extension = Path(path).suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            QMessageBox.critical(
                self,
                "Invalid File",
                "Error: Wrong format. Only json, csv or xlsx are available",
            )
            return

        try:
            dataframe = self._load_dataframe(path)
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(self, "Error loading file", str(exc))
            return

        if dataframe.empty:
            QMessageBox.critical(self, "Error", "The selected file contains no data.")
            return

        self._dataframe = dataframe
        self._current_file_path = path
        self._file_name_label.setText(f"📄 {Path(path).name}")
        self._status_label.setText(f"Loaded {Path(path).name} ({len(dataframe)} row(s)).")
        self._predict_button.setEnabled(True)
        self._reset_button.setEnabled(True)
        self._populate_table(self._input_table, self._dataframe)
        self._prediction_table.setModel(None)
        self._result_label.setText("Ready to predict. Click Predict Power to evaluate.")
        self._set_export_actions_enabled(False)

    def _load_dataframe(self, file_path: str) -> pd.DataFrame:
        extension = Path(file_path).suffix.lower()
        if extension == ".json":
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                data = [data]
            df = pd.DataFrame(data)
        elif extension == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        return df

    def _reset(self):
        self._dataframe = None
        self._current_file_path = None

        self._file_name_label.setText("No file attached.")
        self._status_label.setText("No file loaded.")
        self._result_label.setText("Awaiting input file to run prediction.")

        for table in (self._input_table, self._prediction_table):
            old_model = table.model()
            table.setModel(None)
            if old_model is not None:
                old_model.deleteLater()

        self._predict_button.setEnabled(False)
        self._reset_button.setEnabled(False)
        self._set_export_actions_enabled(False)

    def _populate_table(self, table: QTableView, dataframe: pd.DataFrame):
        old_model = table.model()
        new_model = DataFrameModel(dataframe)
        table.setModel(new_model)
        if old_model is not None:
            old_model.deleteLater()
        table.resizeColumnsToContents()

    def _predict_power(self):
        if self._dataframe is None:
            return

        try:
            predicted_dataframe = self._run_prediction(self._dataframe.copy())
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(self, "Prediction Error", str(exc))
            return

        self._dataframe = predicted_dataframe

        self._set_export_actions_enabled(True)

        self._status_label.setText(
            f"Prediction complete. {len(predicted_dataframe)} row(s) processed."
        )

        if len(predicted_dataframe) == 1:
            row = predicted_dataframe.iloc[0]
            self._result_label.setText(
                f"Dynamic: {row['predicted_dynamic_power_uW']:.4f} µW  |  "
                f"Leakage: {row['predicted_leakage_power_uW']:.4f} µW  |   "
                f"Predicted Total: {row['predicted_total_power_uW']:.4f} µW"
            )
        else:
            total = predicted_dataframe["predicted_total_power_uW"]
            dyn = predicted_dataframe["predicted_dynamic_power_uW"]
            leak = predicted_dataframe["predicted_leakage_power_uW"]
            self._result_label.setText(
                f"Dynamic (avg): {dyn.mean():.4f} µW  |  "
                f"Leakage (avg): {leak.mean():.4f} µW |  "
                f"Total (avg): {total.mean():.4f} µW"
            )

        prediction_columns = [
            "predicted_dynamic_power_uW",
            "predicted_leakage_power_uW",
            "predicted_total_power_uW",
        ]
        self._populate_table(self._prediction_table, predicted_dataframe[prediction_columns])

    def _load_model(self, target_column: str, model_path: Path, input_dim: int) -> torch.nn.Module:
        """
        Load (and cache) the model for a given target column. Rebuilds only
        if that target hasn't been loaded yet, or the expected input
        dimensionality has changed (e.g. a different dataset schema was
        loaded in the same session).
        """
        cached = self._models.get(target_column)
        if cached is not None and cached[1] == input_dim:
            return cached[0]

        if cached is not None:
            old_model, _ = cached
            del old_model
            del self._models[target_column]
            if self._device.type == "cuda":
                torch.cuda.empty_cache()

        model = PowerNet(input_dim).to(self._device)
        state_dict = torch.load(model_path, map_location=self._device, weights_only=True)
        if isinstance(state_dict, torch.nn.Module):
            model = state_dict.to(self._device)
        else:
            model.load_state_dict(state_dict)
        model.eval()

        self._models[target_column] = (model, input_dim)
        return model

    def _predict_target(self, target_column: str, model_path: Path, X_tensor: torch.Tensor) -> np.ndarray:
        model = self._load_model(target_column, model_path, X_tensor.shape[1])
        with torch.no_grad():
            preds_log = model(X_tensor).cpu().numpy().flatten()
        return np.expm1(preds_log)

    def _run_prediction(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        base_dir = Path(__file__).resolve().parent
        preprocessor_path = base_dir / "Model" / "preprocessor.joblib"

        model_paths = {
            target: base_dir / Path(relative_path)
            for target, relative_path in TARGET_CONFIGS.items()
        }
        missing = [str(p) for p in [preprocessor_path, *model_paths.values()] if not p.exists()]
        if missing:
            raise FileNotFoundError(
                "The following model/preprocessor file(s) are missing: " + ", ".join(missing)
            )

        if self._preprocessor is None:
            self._preprocessor = joblib.load(preprocessor_path)
        preprocessor = self._preprocessor

        dataframe = engineer_features(dataframe)
        features, _, _ = get_feature_names()
        X_processed = preprocessor.transform(dataframe[features])

        X_tensor = torch.tensor(X_processed, dtype=torch.float32, device=self._device)

        dataframe = dataframe.reset_index(drop=True)
        for target_column, model_path in model_paths.items():
            predicted_values = self._predict_target(target_column, model_path, X_tensor)

            if len(predicted_values) != len(dataframe):
                raise ValueError(
                    f"Prediction output length for '{target_column}' "
                    f"({len(predicted_values)}) does not match the number of "
                    f"input rows ({len(dataframe)}). This usually means "
                    "engineer_features() dropped or reordered rows."
                )

            dataframe[f"predicted_{target_column}"] = predicted_values

        # total_power_uW is derived, not modeled: it's exactly
        # dynamic + leakage in the data, so summing the two predictions
        # keeps the three reported values internally consistent.
        dataframe["predicted_total_power_uW"] = (
            dataframe["predicted_dynamic_power_uW"] + dataframe["predicted_leakage_power_uW"]
        )

        del X_tensor
        if self._device.type == "cuda":
            torch.cuda.empty_cache()

        return dataframe


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    window = PredictionWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
