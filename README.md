# Early-Stage Digital IC Power Prediction

Source code and experimental data for the Bachelor's Thesis **“Development of
software for predicting power consumption in the early stage of design of
digital integrated circuits.”** The project estimates circuit power from
architectural, physical, switching, and process-voltage-temperature (PVT)
features before expensive sign-off analysis is available.

## Methodology

Total power is represented as the sum of independently learned components:

$$
P_{\text{total}} = P_{\text{dynamic}} + P_{\text{static}}
$$

The production pipeline uses two purpose-built PyTorch residual networks:

- `DynamicResNet` estimates switching-dependent dynamic power.
- `LeakageResNet` estimates static (leakage) power.

Both models operate on log-transformed targets, use the custom `MAPELoss`, and
share a reproducible preprocessing contract saved alongside their weights.
Domain feature engineering supplies physical proxies such as capacitance,
clock-tree load, and voltage/frequency scaling. Training metrics and learning
rates are recorded exclusively through TensorBoard.

## Performance Summary

Evaluation on grouped, unseen circuit designs demonstrates strong generalization
over a wide power range:

- $R^2 > 0.94$
- sMAPE approximately $35\%$
- Filtered MAPE approximately $20\%$ in active power regions

The filtered metric excludes near-zero targets, where ordinary percentage errors
are inherently unstable. These figures should be interpreted together with the
test split and power-region definition used in the thesis experiments.

## Repository Layout

```text
Codes/
├── Datasets/                 Training datasets
├── Results/
│   └── plots.py              Evaluation and analytics visualizations
└── Scripts/
│    ├── model.py              Feature engineering, ResNets, and training pipeline
│    ├── main.py               CLI inference façade (`ICPowerPredictor`)
│    ├── gui.py                PySide6 desktop interface
│    ├── extractor.py          Dataset-row export utility
│    ├── extractor_gui.py      PySide6 data-export interface
│    ├── getter.py             Compatibility wrapper for target export
│    └── Model/                Generated weights and fitted preprocessors
│    └── verilog_paths.txt	  RTL Designs paths for easy finding
└── Validation_Results.py	  5-Fold Cross Validation and SHAP results
Verilog/                      RTL designs used for data collection
environment.yml               Reproducible Conda environment
```

## Installation

Create the supplied Conda environment:

```bash
conda env create -f environment.yml
conda activate diploma_work
```

Alternatively, install the core dependencies with pip:

```bash
pip install torch tensorboard pandas numpy scikit-learn joblib openpyxl pyside6
```

Python 3.9 or newer is required. CUDA is selected automatically when it is
available; inference and training otherwise run on CPU.

## Training

Run from `Codes/Scripts` so the relative dataset and artifact paths resolve:

```bash
python model.py
```

The training pipeline writes the following compatible artifact pairs to `Model/`:

- `dynamic_power_predictor_model.pth` and `preprocessor_dynamic.joblib`
- `leakage_power_predictor_model.pth` and `preprocessor_leakage.joblib`

To inspect the training history:

```bash
tensorboard --logdir runs
```

## Inference

`main.py` presents an `ICPowerPredictor` façade: it validates artifacts, applies
the matching preprocessor, invokes both ResNets, and assembles dynamic, leakage,
and total-power predictions. The command-line layer only reads inputs and
displays or saves results.

```bash
cd Codes/Scripts
python main.py Test/testing.json --output Test/predictions.csv
```

CSV, JSON, XLS, and XLSX input files are accepted. A JSON object represents one
design; a JSON array represents multiple designs. The input must provide the raw
features used by the training pipeline.

## GUI and Analytics

Launch the PySide6 application from `Codes/Scripts`:

```bash
python gui.py
```

For evaluation figures and reports, use `Codes/Results/plots.py`. It loads the
same saved PyTorch artifacts as the CLI, ensuring analytical comparisons remain
consistent with deployed inference.

## Dataset Row Utilities

### Data Exporter GUI

`extractor_gui.py` provides a visual interface for the `extractor.py` and
`getter.py` workflows. Launch it from `Codes/Scripts`:

```bash
python extractor_gui.py
```

Select a source `.csv` dataset, then choose one zero-based **Row index** or an
inclusive **Start Row** to **End Row** range. Once the source is loaded, the
window displays its valid row range. The standard exporter block uses the
selected `features` (default), `targets`, or `all data` mode; the **Quick Get
Targets** block always exports the measured target columns, matching
`getter.py`.

Both blocks write `.json`, `.csv`, or `.xlsx` files. A one-row JSON export is a
single object, while a range JSON export is an array of objects. Source-file,
row-index, range, and output-extension errors are shown directly in the status
bar. The bottom **Features Preview** and **Targets Preview** tables show the
selected row or inclusive range; before a complete selection is entered, they
show the first five dataset rows. The prediction GUI's **Tools → Launch Data
Exporter** action opens this window; the exporter's **Tools → Launch Power
Prediction GUI** action provides the return path.

`extractor.py` exports one row from a collected CSV dataset into a compact file
that can be passed directly to the inference CLI or used as a measured-power
reference. Run these commands from `Codes/Scripts`, where `extractor.py`,
`getter.py`, and `main.py` are located. Row indices are zero-based, so `--row 0`
selects the first data row (not the CSV header).

### `extractor.py`

```bash
python extractor.py SOURCE_CSV OUTPUT_FILE --row ROW_INDEX [--selection SELECTION]
```

The source must be a CSV file with every column required by the selected
export. The destination extension chooses its format: `.json`, `.csv`, or
`.xlsx`. Parent directories for the destination are created automatically.

`--selection` controls the exported column set:

- `features` (default) exports the 34 raw model features required by `main.py`,
  including PVT, cell-count, timing, topology, and switching features.
- `targets` exports the measured `dynamic_power_uW`, `leakage_power_uW`, and
  `total_power_uW` columns.
- `all` exports the model features and all three measured power targets.

Export an inference-ready JSON record from the first encoder test sample:

```bash
cd Codes/Scripts
python extractor.py ../../Verilog/Test/encoder/dataset_power_test_encoder.csv \
    Test/testing.json --row 0 --selection features
```

Export the same row as a one-row CSV containing both inputs and its measured
power values:

```bash
python extractor.py ../../Verilog/Test/encoder/dataset_power_test_encoder.csv \
    Test/encoder-row-0.csv --row 0 --selection all
```

Export only the measured targets to an Excel workbook:

```bash
python extractor.py ../../Verilog/Test/encoder/dataset_power_test_encoder.csv \
    Test/encoder-row-0-targets.xlsx --row 0 --selection targets
```

The command reports an error when the dataset file is absent, the row is outside
the available range, a required feature or target column is missing, or the
output extension is not `.json`, `.csv`, or `.xlsx`.

### `getter.py` compatibility command

`getter.py` is a backward-compatible wrapper around `extractor.py`. It accepts
the same positional arguments and `--row` option, but adds `--selection targets`
when no selection is supplied. This is useful when the historical workflow only
needs the measured values:

```bash
python getter.py ../../Verilog/Test/encoder/dataset_power_test_encoder.csv \
    Test/encoder-row-0-targets.json --row 0
```

You may explicitly override its default selection when needed:

```bash
python getter.py ../../Verilog/Test/encoder/dataset_power_test_encoder.csv \
    Test/encoder-row-0-features.json --row 0 --selection features
```

### End-to-end: inspect one dataset sample with the predictor

The following workflow preserves a clear separation between model inputs and
measured values, allowing a prediction to be compared with the corresponding
dataset target without accidentally supplying target columns as inputs.

1. Export the selected row's features for inference.

   ```bash
   python extractor.py ../../Verilog/Test/encoder/dataset_power_test_encoder.csv \
       Test/encoder-row-0-input.json --row 0 --selection features
   ```
2. Export the same row's measured targets with `getter.py` (or use
   `extractor.py --selection targets`).

   ```bash
   python getter.py ../../Verilog/Test/encoder/dataset_power_test_encoder.csv \
       Test/encoder-row-0-measured.json --row 0
   ```
3. Run inference with the feature-only JSON file and save the model result.

   ```bash
   python main.py Test/encoder-row-0-input.json \
       --output Test/encoder-row-0-prediction.csv
   ```
4. Open `Test/encoder-row-0-measured.json` alongside
   `Test/encoder-row-0-prediction.csv` to compare dynamic, leakage, and total
   power. Both represent the same zero-based source row; the former contains
   measured values in microwatts and the latter contains the model estimates.

For a single audit artifact rather than a feature-only inference input, export
with `--selection all`; retain that file for traceability and use the
feature-only export for `main.py`.
