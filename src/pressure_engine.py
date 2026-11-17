
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/official")
INPUT = BASE / "clean_deliveries.csv"
OUTPUT = BASE / "pressure_deliveries.csv"

df = pd.read_csv(
    INPUT,
    dtype={"season": str},
    low_memory=False
)

# Sort deliveries in match order
df = df.sort_values(
    [
        "match_id",
        "innings",
        "innings_ball_num",
        "overid",
        "over_ball_num"
    ],
    kind="stable"
).reset_index(drop=True)

group = df.groupby(
    ["match_id", "innings"],
    sort=False
)

# Match situation BEFORE the delivery
df["wickets_before"] = (
    group["team_wicket"].cumsum()
    - df["team_wicket"]
)

df["legal_balls_before"] = (
    group["is_legal"].cumsum()
    - df["is_legal"]
)

df["batter_runs_before"] = (
    group["batter_runs"].cumsum()
    - df["batter_runs"]
)

df["wickets_remaining"] = (
    10 - df["wickets_before"]
).clip(lower=0)

# Keep innings stage separate from pressure
df["is_death_over"] = (
    df["phase"] == "Death"
).astype(int)

# Preliminary wicket-related pressure
df["pressure_category"] = "Normal"

df.loc[
    df["wickets_before"].between(4, 5),
    "pressure_category"
] = "Moderate"

df.loc[
    df["wickets_before"] >= 6,
    "pressure_category"
] = "High"

df["is_pressure"] = (
    df["wickets_before"] >= 4
).astype(int)

df["is_high_pressure"] = (
    df["wickets_before"] >= 6
).astype(int)

# Save
df.to_csv(OUTPUT, index=False)

# Validation
print("\n=== UPDATED PRESSURE ENGINE ===")

print("Total deliveries:", len(df))
print("Matches:", df["match_id"].nunique())

print("\nPressure categories:")
print(df["pressure_category"].value_counts())

print("\nPressure by phase:")
print(
    pd.crosstab(
        df["phase"],
        df["pressure_category"]
    )
)

print("\nDeath-over deliveries:",
      df["is_death_over"].sum())

print("\nSaved:", OUTPUT)
