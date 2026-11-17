
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/official")
OUT = BASE / "reliability"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE / "pressure_deliveries.csv",
    dtype={"season": str},
    low_memory=False
)

# Preliminary bowling pressure context
df["bowling_pressure"] = (
    (df["phase"] == "Death") &
    (df["wickets_before"] <= 3)
)

# Runs off bat only: NOT official bowling economy
df["runs_off_bat"] = df["batter_runs"]

df["dot_off_bat"] = (
    (df["batter_runs"] == 0) &
    (df["is_legal"] == 1)
).astype(int)

# Compare within match format and phase
GROUP = [
    "bowler_id",
    "bowler_name",
    "match_format",
    "phase"
]

df["condition"] = np.where(
    df["bowling_pressure"],
    "Pressure",
    "Normal"
)

summary = (
    df.groupby(
        GROUP + ["condition"],
        as_index=False
    )
    .agg(
        matches=("match_id", "nunique"),
        runs=("runs_off_bat", "sum"),
        balls=("is_legal", "sum"),
        wickets=("bowler_wicket", "sum"),
        dots=("dot_off_bat", "sum")
    )
)

normal = summary[
    summary["condition"] == "Normal"
].drop(columns="condition")

pressure = summary[
    summary["condition"] == "Pressure"
].drop(columns="condition")

normal = normal.rename(columns={
    c: "normal_" + c
    for c in ["matches", "runs", "balls", "wickets", "dots"]
})

pressure = pressure.rename(columns={
    c: "pressure_" + c
    for c in ["matches", "runs", "balls", "wickets", "dots"]
})

comparison = normal.merge(
    pressure,
    on=GROUP,
    how="inner"
)

for condition in ["normal", "pressure"]:
    comparison[f"{condition}_bat_run_rate"] = (
        comparison[f"{condition}_runs"] * 6 /
        comparison[f"{condition}_balls"].replace(0, np.nan)
    )

    comparison[f"{condition}_wickets_per_100"] = (
        comparison[f"{condition}_wickets"] * 100 /
        comparison[f"{condition}_balls"].replace(0, np.nan)
    )

comparison["run_rate_improvement"] = (
    comparison["normal_bat_run_rate"] -
    comparison["pressure_bat_run_rate"]
).round(2)

comparison["wicket_rate_improvement"] = (
    comparison["pressure_wickets_per_100"] -
    comparison["normal_wickets_per_100"]
).round(2)

comparison["sufficient_sample"] = (
    (comparison["normal_balls"] >= 30) &
    (comparison["pressure_balls"] >= 24) &
    (comparison["normal_matches"] >= 3) &
    (comparison["pressure_matches"] >= 3)
)

eligible = comparison[
    comparison["sufficient_sample"]
].copy()

eligible = eligible.sort_values(
    ["run_rate_improvement", "wicket_rate_improvement"],
    ascending=False
)

comparison.to_csv(
    OUT / "bowling_comparison_all.csv",
    index=False
)

eligible.to_csv(
    OUT / "bowling_comparison_eligible.csv",
    index=False
)

print("\n=== BOWLING RELIABILITY ANALYSIS ===")
print("Total comparisons:", len(comparison))
print("Eligible comparisons:", len(eligible))

print("\n=== TOP 15 PRELIMINARY BOWLERS ===")
print(
    eligible[
        [
            "bowler_name",
            "match_format",
            "phase",
            "normal_balls",
            "pressure_balls",
            "run_rate_improvement",
            "wicket_rate_improvement"
        ]
    ].head(15).round(2).to_string(index=False)
)

print("\nSaved to:", OUT)
