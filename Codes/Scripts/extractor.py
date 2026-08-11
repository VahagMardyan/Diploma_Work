"""
This code helps to extract a specific row from specific dataset. Available formats: 'csv', 'json' and 'xlsx'.
"""
import pandas as pd
import json

user_input_index = int(input("Index: ")) # real csv index - 2

include_alt = True if input("Alt? (Press any key if yes otherwise press Enter): ") else False

CSV_PATH = f"../../Verilog/Test/dataset_power_test{'_alt' if include_alt else ''}.csv"
# CSV_PATH = f"../../Verilog/Test/decoder/dataset_power_test_decoder.csv"
# CSV_PATH = f"../../Verilog/Test/encoder/dataset_power_test_encoder.csv"

df = pd.read_csv(CSV_PATH)

if user_input_index < 2 or user_input_index > len(df) + 1:
    raise ValueError(f"Index should be between 2 and {len(df) + 1}")

row_data = df.iloc[user_input_index - 2]

required_features = [
    'clock_frequency_mhz', 'toggle_rate', 'static_probability', 'vdd', 'temperature',
    'cell_count', 'comb_cell_count', 'seq_cell_count', 'inv_count', 'buf_count', 
    'nand_count', 'nor_count', 'xor_count', 'mux_count', 'other_count', 
    'total_area', 'num_nets', 'num_inputs', 'num_outputs', 'avg_cell_area', 
    'max_fanout', 'avg_fanout', 'avg_fanin', 'logic_depth', 'depth_mean', 
    'depth_std', 'depth_max', 'avg_net_toggle', 'toggle_attenuation', 
    'critical_path_delay', 'wns', 'tns', 'process', 'pvt_corner'
]

subset = row_data[required_features]

FILE_PATH = "./Test/testing.json"

if FILE_PATH.endswith('.csv'):
    pd.DataFrame([subset]).to_csv(FILE_PATH, index=False)
elif FILE_PATH.endswith('.xlsx'):
    pd.DataFrame([subset]).to_excel(FILE_PATH, index=False)
elif FILE_PATH.endswith('.json'):
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(subset.to_dict(), f, indent=4)
else:
    raise ValueError(f"Error: Wrong format in '{FILE_PATH}'. Only `.json`, `.csv` or `xlsx` are allowed.")

print(f"{user_input_index}-th row (from {CSV_PATH}) saved successfully to {FILE_PATH}.")

