"""Qt desktop interface for exporting model features and measured targets."""

from __future__ import annotations

import subprocess
import sys
import traceback
from pathlib import Path

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QStatusBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from extractor import MODEL_FEATURES, POWER_TARGETS, export_rows


class DataFramePreviewModel(QAbstractTableModel):
    """Read-only dataframe model used by the compact dataset previews."""

    def __init__(self, dataframe: pd.DataFrame) -> None:
        super().__init__()
        self._dataframe = dataframe.reset_index(drop=True)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._dataframe)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter | Qt.AlignVCenter
        if role != Qt.DisplayRole:
            return None
        value = self._dataframe.iat[index.row(), index.column()]
        if pd.isna(value):
            return ""
        return f"{value:.6g}" if isinstance(value, float) else str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        return str(self._dataframe.columns[section]) if orientation == Qt.Horizontal else str(section)


class ExtractorWindow(QMainWindow):
    """Export selected source rows through the shared extractor backend."""

    OUTPUT_EXTENSIONS = {".json", ".csv", ".xlsx"}

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Digital IC Data Exporter")
        self.setMinimumSize(820, 800)
        self._row_count: int | None = None
        self._dataframe: pd.DataFrame | None = None
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(16)

        title = QLabel("Digital IC Data Exporter")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Export model features, measured targets, or both from a CSV dataset.")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        selection_box = QGroupBox("Export Selection")
        selection_layout = QVBoxLayout(selection_box)
        self._selection_group = QButtonGroup(self)
        self._feature_radio = QRadioButton("Features")
        self._target_radio = QRadioButton("Targets")
        self._all_radio = QRadioButton("All data")
        for button, selection in ((self._feature_radio, "features"), (self._target_radio, "targets"), (self._all_radio, "all")):
            button.setProperty("selection", selection)
            self._selection_group.addButton(button)
            selection_layout.addWidget(button)
        self._feature_radio.setChecked(True)
        selection_layout.addStretch()

        source_box = QGroupBox("Source Dataset and Rows")
        source_layout = QVBoxLayout(source_box)
        source_layout.setContentsMargins(12, 16, 12, 14)
        source_layout.setSpacing(10)
        label_width = 140

        self._source_input = QLineEdit()
        self._source_input.setPlaceholderText("Select a source .csv dataset")
        self._source_input.setMinimumHeight(25)
        self._source_input.editingFinished.connect(self._inspect_entered_source)
        source_browse = QPushButton("Browse CSV")
        source_browse.setObjectName("browseButton")
        source_browse.setObjectName("BrowseButton")
        source_browse.setMinimumHeight(25)
        source_browse.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        source_browse.clicked.connect(self._browse_source)
        file_label = QLabel("Input file:")
        file_label.setMinimumWidth(label_width)
        file_label.setObjectName("inputLabel")
        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.setSpacing(15)
        file_row.addWidget(file_label)
        file_row.addWidget(self._source_input, 1)
        file_row.addWidget(source_browse)
        source_layout.addLayout(file_row)

        self._row_index_input = QLineEdit()
        self._row_index_input.setPlaceholderText("e.g. 0")
        self._start_row_input = QLineEdit()
        self._start_row_input.setPlaceholderText("e.g. 0")
        self._end_row_input = QLineEdit()
        self._end_row_input.setPlaceholderText("e.g. 9")
        for field in (self._row_index_input, self._start_row_input, self._end_row_input):
            field.setMinimumHeight(25)
            field.setMaximumWidth(140)
            field.textChanged.connect(self._update_previews)

        index_label = QLabel("Row index:")
        index_label.setMinimumWidth(label_width)
        index_label.setObjectName('inputLabel')
        index_row = QHBoxLayout()
        index_row.setContentsMargins(0, 0, 0, 0)
        index_row.setSpacing(15)
        index_row.addWidget(index_label)
        index_row.addWidget(self._row_index_input, 1)
        index_row.addStretch()
        source_layout.addLayout(index_row)

        range_label = QLabel("Or inclusive range:")
        range_label.setMinimumWidth(label_width)
        range_label.setObjectName('inputLabel')
        range_row = QHBoxLayout()
        range_row.setContentsMargins(0, 0, 0, 0)
        range_row.setSpacing(15)
        range_row.addWidget(range_label)
        range_row.addWidget(self._start_row_input, 1)
        range_row.addWidget(QLabel("to"))
        range_row.addWidget(self._end_row_input, 1)
        range_row.addStretch()
        source_layout.addLayout(range_row)

        self._range_info = QLabel("Choose a CSV file to see the valid row range.")
        self._range_info.setObjectName("rangeInfo")
        self._range_info.setWordWrap(True)
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.addSpacing(label_width + 8)
        info_row.addWidget(self._range_info, 1)
        source_layout.addLayout(info_row)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)
        top_layout.addWidget(source_box, 3)
        top_layout.addWidget(selection_box, 1)
        layout.addLayout(top_layout)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self._make_export_box("Extract Features / Data", "extract"))
        actions_layout.addWidget(self._make_export_box("Quick Get Targets", "targets"))
        layout.addLayout(actions_layout)

        preview_layout = QHBoxLayout()
        self._features_preview = self._make_preview_table()
        self._targets_preview = self._make_preview_table()
        preview_layout.addWidget(self._make_preview_box("Features Preview", self._features_preview))
        preview_layout.addWidget(self._make_preview_box("Targets Preview", self._targets_preview))
        layout.addLayout(preview_layout)
        layout.addStretch()

        self._status = QStatusBar()
        self._status.setObjectName("statusBar")
        self.setStatusBar(self._status)
        self._show_status("Ready. Select a CSV dataset and a row or row range.")

        tools_menu = self.menuBar().addMenu("&Tools")
        prediction_action = tools_menu.addAction("Launch Power Prediction GUI")
        prediction_action.triggered.connect(self._launch_prediction_gui)

    def _make_export_box(self, title: str, mode: str) -> QGroupBox:
        box = QGroupBox(title)
        form = QFormLayout(box)
        output = QLineEdit()
        output.setPlaceholderText("Choose .json, .csv, or .xlsx output")
        default_filename = "extracted_features.json" if mode == "extract" else "extracted_targets.json"
        browse = QPushButton("Output File")
        browse.clicked.connect(lambda: self._browse_output(output, default_filename))
        output_layout = QHBoxLayout()
        output_layout.addWidget(output)
        output_layout.addWidget(browse)
        form.addRow("Output file:", output_layout)
        button = QPushButton("Extract Features / Data" if mode == "extract" else "Quick Get Targets")
        button.setObjectName("extractButton" if mode == "extract" else "targetsButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self._export(output, force_targets=mode == "targets"))
        form.addRow(button)
        if mode == "extract":
            self._extract_output = output
        else:
            self._targets_output = output
        return box

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select source dataset", str(Path(__file__).parent), "CSV Files (*.csv)")
        if not path:
            return
        self._source_input.setText(path)
        self._inspect_source(Path(path))

    def _inspect_entered_source(self) -> None:
        source_text = self._source_input.text().strip()
        if source_text:
            self._inspect_source(Path(source_text))

    def _inspect_source(self, source: Path) -> None:
        if source.suffix.lower() != ".csv":
            self._row_count = None
            self._dataframe = None
            self._clear_previews()
            self._range_info.setText("Invalid source: only .csv files are supported.")
            self._show_status("Error: source dataset must have a .csv extension.", error=True)
            return
        try:
            dataframe = pd.read_csv(source)
            row_count = len(dataframe)
            if not row_count:
                raise ValueError("The selected CSV has no data rows.")
        except Exception as exc:
            self._row_count = None
            self._dataframe = None
            self._clear_previews()
            self._range_info.setText("Unable to read dataset.")
            self._show_status(f"Error reading dataset: {exc}", error=True)
            return
        self._row_count = row_count
        self._dataframe = dataframe
        self._range_info.setText(f"Valid dataset row range: 0 to {row_count - 1}")
        self._show_status(f"Loaded {source.name}: {row_count} data row(s).")
        self._update_previews()

    def _make_preview_table(self) -> QTableView:
        table = QTableView()
        table.setObjectName("previewTable")
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableView.NoEditTriggers)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(150)
        return table

    def _make_preview_box(self, title: str, table: QTableView) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("previewBox")
        box_layout = QVBoxLayout(box)
        box_layout.addWidget(table)
        return box

    def _update_previews(self) -> None:
        if self._dataframe is None:
            self._clear_previews()
            return
        try:
            start_row, end_row = self._selected_rows()
            if start_row < 0 or end_row < start_row or end_row >= len(self._dataframe):
                raise ValueError
            preview_rows = self._dataframe.iloc[start_row : end_row + 1]
        except (TypeError, ValueError):
            # Before a complete valid selection is entered, show a helpful sample.
            preview_rows = self._dataframe.iloc[: min(5, len(self._dataframe))]

        self._set_preview_model(self._features_preview, preview_rows, MODEL_FEATURES)
        self._set_preview_model(self._targets_preview, preview_rows, POWER_TARGETS)

    def _set_preview_model(self, table: QTableView, dataframe: pd.DataFrame, columns: list[str]) -> None:
        available_columns = [column for column in columns if column in dataframe.columns]
        preview = dataframe[available_columns] if available_columns else pd.DataFrame()
        old_model = table.model()
        table.setModel(DataFramePreviewModel(preview))
        if old_model is not None:
            old_model.deleteLater()
        table.resizeColumnsToContents()

    def _clear_previews(self) -> None:
        for table in getattr(self, "_features_preview", None), getattr(self, "_targets_preview", None):
            if table is None:
                continue
            old_model = table.model()
            table.setModel(None)
            if old_model is not None:
                old_model.deleteLater()

    def _browse_output(self, output : QLineEdit, default_name : str = "export.json") -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose export destination",
            default_name,
            "JSON Files (*.json);; CSV Files (*.csv);; Excel Files (*.xlsx)"
        )
        if path:
            output.setText(path)

    def _selected_rows(self) -> tuple[int, int]:
        index_text = self._row_index_input.text().strip()
        start_text = self._start_row_input.text().strip()
        end_text = self._end_row_input.text().strip()
        if index_text and (start_text or end_text):
            raise ValueError("Enter either a row index or a row range, not both.")
        if index_text:
            row = int(index_text)
            return row, row
        if bool(start_text) != bool(end_text):
            raise ValueError("Enter both start and end row values for a range.")
        if start_text:
            return int(start_text), int(end_text)
        raise ValueError("Enter a row index or an inclusive row range.")

    def _export(self, output_field: QLineEdit, force_targets: bool) -> None:
        source = Path(self._source_input.text().strip())
        output = Path(output_field.text().strip())
        try:
            if not source.is_file():
                raise FileNotFoundError("Select an existing source CSV file.")
            if source.suffix.lower() != ".csv":
                raise ValueError("Source dataset must have a .csv extension.")
            if not output.name or output.suffix.lower() not in self.OUTPUT_EXTENSIONS:
                raise ValueError("Output file must end in .json, .csv, or .xlsx.")
            if self._row_count is None:
                self._inspect_source(source)
                if self._row_count is None:
                    return
            start_row, end_row = self._selected_rows()
            selection = "targets" if force_targets else self._selection_group.checkedButton().property("selection")
            export_rows(source, output, start_row, end_row, selection)
        except (FileNotFoundError, IndexError, OSError, ValueError) as exc:
            self._show_status(f"Export failed: {exc}", error=True)
            return
        except Exception as exc:  # Surface unexpected write/engine failures in the GUI.
            traceback.print_exc()
            self._show_status(f"Export failed: {exc}", error=True)
            return
        row_text = str(start_row) if start_row == end_row else f"{start_row} to {end_row}"
        self._show_status(f"Exported row(s) {row_text} as {selection} to {output.name}.")

    def _launch_prediction_gui(self) -> None:
        gui_path = Path(__file__).with_name("gui.py")
        try:
            subprocess.Popen([sys.executable, str(gui_path)], cwd=str(gui_path.parent))
        except OSError as exc:
            self._show_status(f"Could not launch prediction GUI: {exc}", error=True)

    def _show_status(self, message: str, error: bool = False) -> None:
        self._status.showMessage(message)
        self._status.setProperty("error", error)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)

    def _apply_style(self) -> None:
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#121212"))
        palette.setColor(QPalette.WindowText, QColor("#EEEEEE"))
        palette.setColor(QPalette.Base, QColor("#1E1E1E"))
        palette.setColor(QPalette.Text, QColor("#EEEEEE"))
        palette.setColor(QPalette.Button, QColor("#1E1E1E"))
        palette.setColor(QPalette.ButtonText, QColor("#EEEEEE"))
        palette.setColor(QPalette.Highlight, QColor("#3A8DFF"))
        QApplication.instance().setPalette(palette)
        self.setStyleSheet("""
            QMainWindow { background: #121212; }
            QLabel#titleLabel { font-size: 26px; font-weight: 700; color: #FFFFFF; }
            QLabel#subtitleLabel, QLabel#rangeInfo { color: #CCCCCC; font-size: 14px; }
            QLabel#rangeInfo { font-size: 12px; }
            QLabel#inputLabel { font-size: 14px; padding: 5px; }
            QPushButton#BrowseButton { font-size: 11px; padding: 8px; }
            QGroupBox { background: #191919; border: 1px solid #2E2E2E; border-radius: 12px; margin-top: 12px; padding: 12px; font-weight: 700; color: #FFFFFF; }
            QGroupBox::title { subcontrol-origin: padding; left: 12px; padding: 0 5px; background: #191919; }
            QLineEdit { background: #141414; border: 1px solid #3A3A3A; border-radius: 8px; color: #EEEEEE; padding: 5px 5px; font-size: 12px; }
            QLineEdit:focus { border-color: #3A8DFF; }
            QRadioButton { color: #DDDDDD; padding: 5px 12px; }
            QRadioButton::indicator { width: 15px; height: 15px; }
            QPushButton { border: none; border-radius: 10px; padding: 8px 16px; font-size: 14px; background: #2F80ED; color: #FFFFFF; }
            QPushButton:hover { background: #4A90FF; }
            QPushButton#extractButton { background: #12B886; }
            QPushButton#extractButton:hover { background: #1CD88C; }
            QPushButton#targetsButton { background: #7C5CE0; }
            QPushButton#targetsButton:hover { background: #9374F0; }
            QGroupBox#previewBox { padding: 6px; }
            QTableView#previewTable { background: #141414; border: 1px solid #2E2E2E; gridline-color: #2E2E2E; color: #EEEEEE; }
            QHeaderView::section { background: #1F1F1F; color: #EEEEEE; padding: 6px; border: none; }
            QTableView::item { padding: 6px; }
            QTableView::item:selected { background: #3A6ED8; color: #FFFFFF; }
            QStatusBar { background: #191919; color: #DDDDDD; border-top: 1px solid #2E2E2E; padding: 5px; }
            QStatusBar[error="true"] { color: #FF7B7B; }
        """)


def main() -> None:
    app = QApplication([])
    app.setStyle("Fusion")
    window = ExtractorWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
