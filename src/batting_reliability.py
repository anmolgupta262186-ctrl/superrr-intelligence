
from pathlib import Path
import pandas as pd

BASE = Path("data/processed/official")
OUT = BASE / "reliability"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE / "pressure_deliveries.csv",
    dtype={"season": str},
    low_memory=False
)

# Only deliveries faced by batters
bat = df[df["batter_ball"] == 1].copy()

bat["condition"] = bat["is_pressure"].map({
    0: "Normal",
    1: "Pressure"
})

bat["dot"] = (bat["batter_runs"] == 0).astype(int)

# Compare within the same phase and match format
GROUP = [
    "striker_id",
    "striker_name",
    "match_format",
    "phase"
]

summary = (
    bat.groupby(
        GROUP + ["condition"],
        as_index=False
    )
    .agg(
        matches=("match_id", "nunique"),
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum"),
        dots=("dot", "sum"),
        boundaries=("is_boundary", "sum")
    )
)

normal = summary[
    summary["condition"] == "Normal"
].drop(columns="condition")

pressure = summary[
    summary["condition"] == "Pressure"
].drop(columns="condition")

normal = normal.rename(columns={
    "matches": "normal_matches",
    "runs": "normal_runs",
    "balls": "normal_balls",
    "dots": "normal_dots",
    "boundaries": "normal_boundaries"
})

pressure = pressure.rename(columns={
    "matches": "pressure_matches",
    "runs": "pressure_runs",
    "balls": "pressure_balls",
    "dots": "pressure_dots",
    "boundaries": "pressure_boundaries"
})

comparison = normal.merge(
    pressure,
    on=GROUP,
    how="inner",
    validate="one_to_one"
)

# Normal and pressure scoring rates
comparison["normal_sr"] = (
    100 * comparison["normal_runs"] /
    comparison["normal_balls"]
).round(2)

comparison["pressure_sr"] = (
    100 * comparison["pressure_runs"] /
    comparison["pressure_balls"]
).round(2)

comparison["sr_difference"] = (
    comparison["pressure_sr"] -
    comparison["normal_sr"]
).round(2)

# Dot-ball comparison
comparison["normal_dot_pct"] = (
    100 * comparison["normal_dots"] /
    comparison["normal_balls"]
).round(2)

comparison["pressure_dot_pct"] = (
    100 * comparison["pressure_dots"] /
    comparison["pressure_balls"]
).round(2)

comparison["dot_pct_difference"] = (
    comparison["pressure_dot_pct"] -
    comparison["normal_dot_pct"]
).round(2)

# Preliminary sample-size eligibility
comparison["sufficient_sample"] = (
    (comparison["normal_balls"] >= 30) &
    (comparison["pressure_balls"] >= 20) &
    (comparison["normal_matches"] >= 3) &
    (comparison["pressure_matches"] >= 3)
)

comparison.to_csv(
    OUT / "batting_pressure_comparison_all.csv",
    index=False
)

eligible = comparison[
    comparison["sufficient_sample"]
].copy()

eligible = eligible.sort_values(
    "sr_difference",
    ascending=False
)

eligible.to_csv(
    OUT / "batting_pressure_comparison_eligible.csv",
    index=False
)

print("\n=== BATTING PRESSURE COMPARISON ===")

print("Unique batters:", bat["striker_id"].nunique())
print("Player-format-phase comparisons:", len(comparison))
print("Comparisons with sufficient samples:", len(eligible))

print("\n=== TOP 15 STRIKE-RATE IMPROVEMENTS ===")

print(
    eligible[
        [
            "striker_name",
            "match_format",
            "phase",
            "normal_balls",
            "pressure_balls",
            "normal_sr",
            "pressure_sr",
            "sr_difference",
            "dot_pct_difference"
        ]
    ].head(15).to_string(index=False)
)

print("\nSaved results to:", OUT)
