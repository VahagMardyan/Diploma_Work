import pandas as pd

file_path1 = "dataset_power_alt.csv"
file_path2 = "dataset_power.csv"

df1 = pd.read_csv(file_path1)
df2 = pd.read_csv(file_path2)

df = pd.concat([df1, df2], ignore_index=True)

numeric_df = df.select_dtypes(include=['number'])

ranges = numeric_df.agg(['min', 'max']).transpose()

print("Columns value range: [min, max]")
print(ranges)

ranges.to_csv("dataset_ranges.csv")

