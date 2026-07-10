import pandas as pd
from sklearn.model_selection import train_test_split

print("Loading and preparing data for split inspection...")

try:
    df_1 = pd.read_csv("../Dataset/dataset_old_pairs/dataset_power_1.csv")
    df_2 = pd.read_csv("../Dataset/dataset_new_pairs/dataset_power_2.csv")
except FileNotFoundError:
    df_1 = pd.read_csv("dataset_power_1.csv")
    df_2 = pd.read_csv("dataset_power_2.csv")

df = pd.concat([df_1, df_2], ignore_index=True)

redundant_designs = ['full_half_add_1bit', 'mux_condt']
df = df[~df['design_name'].isin(redundant_designs)].reset_index(drop=True)

train_idx, temp_idx = train_test_split(df.index, test_size=0.30, random_state=42)

val_idx, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=42)

df['split_set'] = 'Unknown'
df.loc[train_idx, 'split_set'] = 'Train'
df.loc[val_idx, 'split_set'] = 'Validation'
df.loc[test_idx, 'split_set'] = 'Test'

print("\nDistribution of Designs Among Sets")
print("="*30)
pivot_summary = df.pivot_table(index='design_name', columns='split_set', aggfunc='size', fill_value=0)
print(pivot_summary)
print('='*30)

output_filename = '../Dataset/dataset_with_split_labels.csv'
df.to_csv(output_filename, index=False)
print(f'\n The complete database with the appropriate labels has been saved in the `{output_filename}` file.')

