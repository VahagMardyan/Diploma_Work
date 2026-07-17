"""
This code shows the range of permissible parameter values: [min; max]
"""
import pandas as pd

file_path1 = "dataset_power_alt.csv"
file_path2 = "dataset_power.csv"

# file_path1 = "../../Verilog/Test/dataset_power_test_alt.csv"
# file_path2 = "../../Verilog/Test/dataset_power_test.csv"

df1 = pd.read_csv(file_path1)
df2 = pd.read_csv(file_path2)

df = pd.concat([df1, df2], ignore_index=True)

numeric_df = df.select_dtypes(include=['number'])

ranges = numeric_df.agg(['min', 'max']).transpose()

RANGE_PATH = "../Datasets/Ranges/dataset_ranges.csv"

ranges.to_csv(RANGE_PATH)
print(f"Ranges saved into {RANGE_PATH}")

