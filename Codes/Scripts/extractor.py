import pandas as pd
import json

df = pd.read_csv('../Datasets/dataset_power.csv')

user_input_index = 17 # real csv index - 2

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

FILE_PATH = "./Test/test.json"
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    json.dump(subset.to_dict(), f, indent=4)

print(f"{user_input_index}-th row saved successfully to {FILE_PATH}!")