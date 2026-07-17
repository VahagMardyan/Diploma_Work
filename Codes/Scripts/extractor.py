import pandas as pd
import json

df = pd.read_csv('../../Verilog/Test/dataset_power_test.csv')

user_input_index = 2400 # real csv index - 2

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

FILE_PATH = "./Test/test.xlsx"

if FILE_PATH.endswith('.csv'):
    pd.DataFrame([subset]).to_csv(FILE_PATH, index=False)
elif FILE_PATH.endswith('.xlsx'):
    pd.DataFrame([subset]).to_excel(FILE_PATH, index=False)
elif FILE_PATH.endswith('.json'):
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(subset.to_dict(), f, indent=4)
else:
    raise ValueError(f"Error: Wrong format in '{FILE_PATH}'. Only `.json`, `.csv` or `xlsx` are allowed.")

print(f"{user_input_index}-th row saved successfully to {FILE_PATH}.")

