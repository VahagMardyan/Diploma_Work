import pandas as pd
import json

user_input_index = int(input("Index: ")) # real csv index - 2

include_alt = True if input("Alt? (Press any key if yes otherwise press Enter): ") else False

CSV_PATH = f"../../Verilog/Test/dataset_power_test{'_alt' if include_alt else ''}.csv"

df = pd.read_csv(CSV_PATH)

if user_input_index < 2 or user_input_index > len(df) + 1:
    raise ValueError(f"Index should be between 2 and {len(df) + 1}")

row_data = df.iloc[user_input_index - 2]

required_features = [
    'dynamic_power_uW', 'leakage_power_uW', 'total_power_uW'
]

subset = row_data[required_features]

file_path = './Test/real_power.json'

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(subset.to_dict(), f, indent=4)

print(f"{user_input_index}-th row (from '{CSV_PATH}' ) saved successfully to {file_path}.")