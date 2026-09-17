import glob
import os
import pandas as pd

folder_path = "./"
csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
print(f"Found: {len(csv_files)}")

df_list = []
for file in csv_files:
    try:
        temp_df = pd.read_csv(file)
        df_list.append(temp_df)
        print(f"{file} - {len(temp_df)} rows")
    except Exception as e:
        print(f"Error in {file}: {e}")

if df_list:
    df = pd.concat(df_list, ignore_index=True)
    df = df.sort_values(
        by = ["design_name", "clock_frequency_mhz"], ascending = [True, True]
    )

    print(f"Merged & Sorted: {len(df)} rows")

    output_file = "dataset.csv"
    df.to_csv(output_file, index = False)
else:
    print("CSV files not found")
