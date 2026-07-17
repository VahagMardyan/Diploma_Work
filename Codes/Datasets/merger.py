import pandas as pd
import glob
import os

folder_path = "./"
csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
print(f"Founded: {len(csv_files)}")

df_list = []
for file in csv_files:
    try:
        temp_df = pd.read_csv(file)
        df_list.append(temp_df)
        print(f"{file} - {len(temp_df)} rows")
    except Exception as e:
        print(f"Error: in {file}: {e}")

if df_list:
    df = pd.concat(df_list, ignore_index=True)
    print(f"Merged: {len(df)} rows")

    output_file = "dataset_power_alt.csv"
    df.to_csv(output_file, index = False)
    print(f"Saved: {output_file}")
else:
    print("CSV files not found")
