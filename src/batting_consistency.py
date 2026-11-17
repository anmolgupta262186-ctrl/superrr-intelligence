
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

# Count dismissals only for the player who was dismissed.
# A non-striker run-out is not charged to the striker.
df["striker_out"] = (
    df["dismissed_player_id"] == df["striker_id"]
).astype(int)

df["condition"] = np.where(
    df["is_pressure"] == 1,
    "Pressure",
    "Normal"
)

GROUP = [
    "striker_id", "striker_name",
    "match_format", "phase"
]

# -----------------------------------
# 1. PERFORMANCE BY CONDITION
# -----------------------------------

summary = (
    df.groupby(
        GROUP + ["condition"],
        as_index=False
    )
    .agg(
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum"),
        dismissals=("striker_out", "sum"),
        matches=("match_id", "nunique")
    )
)

summary["strike_rate"] = (
    summary["runs"] * 100 /
    summary["balls"].replace(0, np.nan)
)

summary["dismissal_per_100_balls"] = (
    summary["dismissals"] * 100 /
    summary["balls"].replace(0, np.nan)
)

normal = summary[
    summary["condition"] == "Normal"
].drop(columns="condition")

pressure = summary[
    summary["condition"] == "Pressure"
].drop(columns="condition")

normal = normal.rename(columns={
    c: "normal_" + c
    for c in ["runs", "balls", "dismissals",
              "matches", "strike_rate",
              "dismissal_per_100_balls"]
})

pressure = pressure.rename(columns={
    c: "pressure_" + c
    for c in ["runs", "balls", "dismissals",
              "matches", "strike_rate",
              "dismissal_per_100_balls"]
})

comparison = normal.merge(
    pressure,
    on=GROUP,
    how="inner",
    validate="one_to_one"
)

comparison["sr_change"] = (
    comparison["pressure_strike_rate"] -
    comparison["normal_strike_rate"]
)

comparison["dismissal_risk_change"] = (
    comparison["pressure_dismissal_per_100_balls"] -
    comparison["normal_dismissal_per_100_balls"]
)

# -----------------------------------
# 2. PRESSURE MATCH CONSISTENCY
# -----------------------------------

pressure_balls = df[
    df["is_pressure"] == 1
].copy()

per_match = (
    pressure_balls.groupby(
        GROUP + ["match_id"],
        as_index=False
    )
    .agg(
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum"),
        dismissals=("striker_out", "sum")
    )
)

# Ignore tiny match samples for consistency
per_match = per_match[
    per_match["balls"] >= 6
].copy()

per_match["match_sr"] = (
    per_match["runs"] * 100 /
    per_match["balls"]
)

consistency = (
    per_match.groupby(GROUP, as_index=False)
    .agg(
        evaluated_matches=("match_id", "nunique"),
        median_pressure_sr=("match_sr", "median"),
        pressure_sr_std=("match_sr", "std"),
        matches_sr_120=(
            "match_sr",
            lambda x: (x >= 120).sum()
        )
    )
)

consistency["success_rate_pct"] = (
    consistency["matches_sr_120"] * 100 /
    consistency["evaluated_matches"]
)

comparison = comparison.merge(
    consistency,
    on=GROUP,
    how="left"
)

# -----------------------------------
# 3. SAMPLE-SIZE FILTER
# -----------------------------------

eligible = comparison[
    (comparison["normal_balls"] >= 30) &
    (comparison["pressure_balls"] >= 30) &
    (comparison["normal_matches"] >= 3) &
    (comparison["pressure_matches"] >= 3) &
    (comparison["evaluated_matches"] >= 3)
].copy()

# Provisional sorting only, not final rankings
eligible = eligible.sort_values(
    ["sr_change", "success_rate_pct"],
    ascending=[False, False]
)

comparison.to_csv(
    OUT / "batting_consistency_all.csv",
    index=False
)

eligible.to_csv(
    OUT / "batting_consistency_eligible.csv",
    index=False
)

print("\n=== BATTING CONSISTENCY ANALYSIS ===")
print("Total comparisons:", len(comparison))
print("Eligible comparisons:", len(eligible))

print("\n=== TOP 15 PRELIMINARY CANDIDATES ===")

print(
    eligible[
        [
            "striker_name", "match_format", "phase",
            "normal_balls", "pressure_balls",
            "sr_change", "dismissal_risk_change",
            "evaluated_matches", "success_rate_pct"
        ]
    ].head(15).round(2).to_string(index=False)
)

print("\nSaved to:", OUT)
