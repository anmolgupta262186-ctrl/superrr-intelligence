
from pathlib import Path
import pandas as pd

BASE = Path("data/raw/rr_official")
df = pd.read_csv(BASE / "ball_by_ball.csv")

print("\n=== EXTRAS VALIDATION ===")
print(
    df.groupby("extras_type", dropna=False)
    .agg(
        deliveries=("match_id", "size"),
        batter_runs=("runs", "sum"),
        extras1=("extras1_runs", "sum"),
        extras2=("extras_2_runs", "sum")
    ).to_string()
)

print("\n=== OVER DELIVERY COUNTS ===")
print(
    df.groupby(["match_id", "innings", "overid"])
    .size()
    .value_counts()
    .sort_index()
)

print("\n=== INNINGS DISTRIBUTION ===")
print(df["innings"].value_counts().sort_index())

print("\n=== REVISED MATCHES ===")
matches = pd.read_csv(BASE / "matches.csv")
print("Matches with revised targets:",
      matches["revised_target"].notna().sum())

print("Matches with revised first innings:",
      matches["first_inn_revised_overs"].notna().sum())

print("Matches with revised second innings:",
      matches["second_inn_revised_overs"].notna().sum())
