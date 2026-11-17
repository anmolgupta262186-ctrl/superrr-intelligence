
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/raw/rr_official")

files = sorted(DATA_DIR.glob("*.csv"))

print("\n=== OFFICIAL DATA PACK SCHEMA ===")

for file in files:
    print(f"\nFILE: {file.name}")

    df = pd.read_csv(file, nrows=5)

    print("Columns:")
    for column in df.columns:
        print(" -", column)

    print("\nSample data types:")
    print(df.dtypes.to_string())

    print("-" * 60)

print("\nSchema inspection completed.")
