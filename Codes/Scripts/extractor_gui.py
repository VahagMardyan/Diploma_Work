"""Qt desktop interface for exporting model features and measured targets."""

from __future__ import annotations

import subprocess
import sys
import traceback
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
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
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from extractor import export_rows


class ExtractorWindow(QMainWindow):
    """Export selected source rows through the shared extractor backend."""

    OUTPUT_EXTENSIONS = {".json", ".csv", ".xlsx"}

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Digital IC Data Exporter")
        self.setMinimumSize(820, 560)
        self._row_count: int | None = None
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
        selection_layout = QHBoxLayout(selection_box)
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
        layout.addWidget(selection_box)

        source_box = QGroupBox("Source Dataset and Rows")
        source_layout = QGridLayout(source_box)
        self._source_input = QLineEdit()
        self._source_input.setPlaceholderText("Select a source .csv dataset")
        source_browse = QPushButton("Browse CSV")
        source_browse.setObjectName("browseButton")
        source_browse.clicked.connect(self._browse_source)
        source_layout.addWidget(QLabel("Input file:"), 0, 0)
        source_layout.addWidget(self._source_input, 0, 1)
        source_layout.addWidget(source_browse, 0, 2)

        self._row_index_input = QLineEdit()
        self._row_index_input.setPlaceholderText("e.g. 0")
        self._start_row_input = QLineEdit()
        self._start_row_input.setPlaceholderText("e.g. 0")
        self._end_row_input = QLineEdit()
        self._end_row_input.setPlaceholderText("e.g. 9")
        source_layout.addWidget(QLabel("Row index:"), 1, 0)
        source_layout.addWidget(self._row_index_input, 1, 1, 1, 2)
        source_layout.addWidget(QLabel("Or inclusive range:"), 2, 0)
        range_layout = QHBoxLayout()
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.addWidget(self._start_row_input)
        range_layout.addWidget(QLabel("to"))
        range_layout.addWidget(self._end_row_input)
        source_layout.addLayout(range_layout, 2, 1, 1, 2)
        self._range_info = QLabel("Choose a CSV file to see the valid row range.")
        self._range_info.setObjectName("rangeInfo")
        source_layout.addWidget(self._range_info, 3, 1, 1, 2)
        layout.addWidget(source_box)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self._make_export_box("Extract Features / Data", "extract"))
        actions_layout.addWidget(self._make_export_box("Quick Get Targets", "targets"))
        layout.addLayout(actions_layout)
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
        browse = QPushButton("Output File")
        browse.clicked.connect(lambda: self._browse_output(output))
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

    def _inspect_source(self, source: Path) -> None:
        if source.suffix.lower() != ".csv":
            self._row_count = None
            self._range_info.setText("Invalid source: only .csv files are supported.")
            self._show_status("Error: source dataset must have a .csv extension.", error=True)
            return
        try:
            row_count = len(pd.read_csv(source))
            if not row_count:
                raise ValueError("The selected CSV has no data rows.")
        except Exception as exc:
            self._row_count = None
            self._range_info.setText("Unable to read dataset.")
            self._show_status(f"Error reading dataset: {exc}", error=True)
            return
        self._row_count = row_count
        self._range_info.setText(f"Valid dataset row range: 0 to {row_count - 1}")
        self._show_status(f"Loaded {source.name}: {row_count} data row(s).")

    def _browse_output(self, output: QLineEdit) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Choose export destination", "export.json", "JSON Files (*.json);;CSV Files (*.csv);;Excel Files (*.xlsx)")
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
            QGroupBox { background: #191919; border: 1px solid #2E2E2E; border-radius: 12px; margin-top: 12px; padding: 12px; font-weight: 700; color: #FFFFFF; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
            QLineEdit { background: #141414; border: 1px solid #3A3A3A; border-radius: 8px; color: #EEEEEE; padding: 9px; }
            QLineEdit:focus { border-color: #3A8DFF; }
            QRadioButton { color: #DDDDDD; padding: 5px 12px; }
            QRadioButton::indicator { width: 15px; height: 15px; }
            QPushButton { border: none; border-radius: 10px; padding: 10px 16px; font-size: 14px; background: #2F80ED; color: #FFFFFF; }
            QPushButton:hover { background: #4A90FF; }
            QPushButton#extractButton { background: #12B886; }
            QPushButton#extractButton:hover { background: #1CD88C; }
            QPushButton#targetsButton { background: #7C5CE0; }
            QPushButton#targetsButton:hover { background: #9374F0; }
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
