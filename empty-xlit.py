import pandas as pd

# Path to the CSV file
csv_file_path = 'dataset/xlits.csv'

# Read the CSV file into a DataFrame
df = pd.read_csv(csv_file_path)

# Identify rows where 'xlit' is empty or NaN
empty_xlit_rows = df[df['xlit'].isnull() | (df['xlit'].astype(str).str.strip() == '')]

# Print 'sign' and 'canonical' values for these rows
for index, row in empty_xlit_rows.iterrows():
    print(f"Sign: {row['sign']}, Canonical: {row['canonical']}, PUA: U+{hex(0xE000 + int(row['sign']))[2:].upper()}")

