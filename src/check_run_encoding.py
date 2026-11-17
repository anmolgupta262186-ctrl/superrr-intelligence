
import pandas as pd
from pathlib import Path

BASE = Path("data/raw/rr_official")

df = pd.read_csv(BASE / "ball_by_ball.csv")

# Compare run-related columns
print("\n=== RUN COLUMN STATISTICS ===")

for col in ["runs", "extras1_runs", "extras_2_runs"]:
    print(f"\n{col}")
    print(df[col].describe())

print("\n=== MOST COMMON EXTRAS1 VALUES ===")
print(df["extras1_runs"].value_counts().head(15))

print("\n=== SAMPLE DELIVERY PATTERNS ===")

samples = pd.concat([
    df[df["extras_type"].isna()].head(5),
    df[df["extras_type"] == "wide"].head(5),
    df[df["extras_type"] == "Overstep"].head(5),
    df[df["extras_type"] == "byes"].head(5)
])

print(
    samples[
        [
            "runs",
            "extras_type",
            "extras1_runs",
            "extras_2_runs",
            "is_four",
            "is_six"
        ]
    ].to_string(index=False)
)

print("\n=== POTENTIAL DATA QUALITY ISSUES ===")

print(
    "Negative extras1:",
    (df["extras1_runs"] < 0).sum()
)

print(
    "Extras1 greater than 10:",
    (df["extras1_runs"] > 10).sum()
)

print(
    "Missing extras1:",
    df["extras1_runs"].isna().sum()
)
