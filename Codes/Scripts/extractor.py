"""Export a dataset row as model features, measured targets, or both."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

import pandas as pd

MODEL_FEATURES = [
    "clock_frequency_mhz", "toggle_rate", "static_probability", "vdd",
    "temperature", "cell_count", "comb_cell_count", "seq_cell_count",
    "inv_count", "buf_count", "nand_count", "nor_count", "xor_count",
    "mux_count", "other_count", "total_area", "num_nets", "num_inputs",
    "num_outputs", "avg_cell_area", "max_fanout", "avg_fanout", "avg_fanin",
    "logic_depth", "depth_mean", "depth_std", "depth_max", "avg_net_toggle",
    "toggle_attenuation", "critical_path_delay", "wns", "tns", "process",
    "pvt_corner",
]
POWER_TARGETS = ["dynamic_power_uW", "leakage_power_uW", "total_power_uW"]


def print_usage_example() -> None:
    """Print user-friendly usage instructions and examples."""
    print("""
================================================================================
 EXTRACTOR UTILITY USAGE EXAMPLES
================================================================================
Usage:
  python extractor.py <source_csv> <output_file> --row <index> [--selection <type>]

Options for --selection:
  features  : Export model input features only (Default)
  targets   : Export ground-truth power targets only
  all       : Export both features and power targets

Examples:
  1. Extract row 0 input features to JSON (for prediction testing):
     python extractor.py ../Datasets/dataset_power.csv Test/sample.json --row 0

  2. Extract row 5 full data (all columns) to CSV:
     python extractor.py ../Datasets/dataset_power.csv Test/sample.csv --row 5 --selection all
================================================================================
""")


def select_columns(dataframe: pd.DataFrame, selection: str) -> list[str]:
    """Return the column contract for an export selection."""
    selections = {
        "features": MODEL_FEATURES,
        "targets": POWER_TARGETS,
        "all": MODEL_FEATURES + POWER_TARGETS,
    }
    columns = selections[selection]
    missing = sorted(set(columns).difference(dataframe.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    return columns


def export_row(
    source: Path,
    output: Path,
    row_index: int,
    selection: str,
) -> None:
    """Export one zero-based CSV row in JSON, CSV, or Excel format.

    Args:
        source: Source CSV dataset.
        output: Destination file ending in ``.json``, ``.csv``, or ``.xlsx``.
        row_index: Zero-based index of the row to export.
        selection: ``features``, ``targets``, or ``all``.
    """
    export_rows(source, output, row_index, row_index, selection)


def export_rows(
    source: Path,
    output: Path,
    start_row: int,
    end_row: int,
    selection: str,
) -> None:
    """Export an inclusive zero-based range of CSV rows.

    This is the shared API for graphical callers. ``export_row`` remains the
    public single-record API and command-line interface used by existing tools.
    """
    if not source.is_file():
        raise FileNotFoundError(f"Source dataset not found: {source}")
    if source.suffix.lower() != ".csv":
        raise ValueError("Source dataset must be a CSV file.")
    if selection not in {"features", "targets", "all"}:
        raise ValueError("Selection must be features, targets, or all.")

    dataframe = pd.read_csv(source)
    if dataframe.empty:
        raise ValueError("Source dataset contains no data rows.")
    if start_row > end_row:
        raise ValueError("Start row cannot be greater than end row.")
    if start_row < 0 or end_row >= len(dataframe):
        raise IndexError(f"Row indices must be between 0 and {len(dataframe) - 1}.")

    records = dataframe.iloc[start_row : end_row + 1][select_columns(dataframe, selection)]
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".json":
        with output.open("w", encoding="utf-8") as output_file:
            if len(records) == 1:
                json.dump(records.iloc[0].to_dict(), output_file, indent=2)
            else:
                json.dump(records.to_dict(orient="records"), output_file, indent=2)
    elif output.suffix.lower() == ".csv":
        records.to_csv(output, index=False)
    elif output.suffix.lower() == ".xlsx":
        records.to_excel(output, index=False)
    else:
        raise ValueError("Output format must be JSON, CSV, or XLSX.")


def build_parser() -> argparse.ArgumentParser:
    """Build the row-export command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Source CSV dataset.")
    parser.add_argument(
        "output", type=Path, help="Destination .json, .csv, or .xlsx file."
    )
    parser.add_argument("--row", type=int, required=True, help="Zero-based row index.")
    parser.add_argument(
        "--selection",
        choices=("features", "targets", "all"),
        default="features",
        help="Columns to export (default: %(default)s).",
    )
    return parser


def main(arguments: Optional[Sequence[str]] = None) -> int:
    """Execute the row exporter and return a process status code."""
    provided_args = list(sys.argv[1:] if arguments is None else arguments)

    # Display clean usage text if run without arguments or with -h/--help
    if not provided_args or provided_args[0] in ("-h", "--help"):
        print_usage_example()
        return 0

    parsed = build_parser().parse_args(provided_args)
    try:
        export_row(parsed.source, parsed.output, parsed.row, parsed.selection)
    except (FileNotFoundError, IndexError, OSError, ValueError) as error:
        print(f"Export failed: {error}")
        return 1
    print(f"Exported row {parsed.row} from {parsed.source} to {parsed.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
