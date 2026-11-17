
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/official")
OUT = BASE / "pri"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE / "match_state_pressure.csv",
    dtype={"season": str},
    low_memory=False
)

# -----------------------------------
# 1. SELECT PRESSURE CATEGORIES
# -----------------------------------

df = df[
    df["batting_pressure_category"].isin(
        ["Normal", "High"]
    )
].copy()

df["condition"] = df["batting_pressure_category"]

KEYS = ["striker_id", "striker_name",
        "match_format", "phase"]

# Identify striker dismissals
df["dismissal"] = (
    df["dismissed_player_id"] == df["striker_id"]
).astype(int)

# -----------------------------------
# 2. AGGREGATE BATTING PERFORMANCE
# -----------------------------------

stats = (
    df.groupby(KEYS + ["condition"])
    .agg(
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum"),
        dismissals=("dismissal", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

stats = stats[stats["balls"] > 0].copy()

stats["sr"] = (
    100 * stats["runs"] / stats["balls"]
)

stats["dismissal_rate"] = (
    100 * stats["dismissals"] / stats["balls"]
)

# -----------------------------------
# 3. NORMAL VS PRESSURE PERFORMANCE
# -----------------------------------

normal = stats[
    stats["condition"] == "Normal"
].drop(columns="condition")

pressure = stats[
    stats["condition"] == "High"
].drop(columns="condition")

result = normal.merge(
    pressure,
    on=KEYS,
    suffixes=("_normal", "_pressure")
)

result["sr_improvement"] = (
    result["sr_pressure"] -
    result["sr_normal"]
)

result["dismissal_improvement"] = (
    result["dismissal_rate_normal"] -
    result["dismissal_rate_pressure"]
)

# -----------------------------------
# 4. MATCH-TO-MATCH CONSISTENCY
# -----------------------------------

pressure_df = df[
    df["condition"] == "High"
]

match_stats = (
    pressure_df.groupby(KEYS + ["match_id"])
    .agg(
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum")
    )
    .reset_index()
)

# Avoid evaluating extremely short appearances
match_stats = match_stats[
    match_stats["balls"] >= 6
].copy()

match_stats["match_sr"] = (
    100 * match_stats["runs"] /
    match_stats["balls"]
)

# Compare each appearance with player's normal SR
match_stats = match_stats.merge(
    normal[KEYS + ["sr"]],
    on=KEYS,
    how="inner"
)

match_stats["successful"] = (
    match_stats["match_sr"] >= match_stats["sr"]
).astype(int)

consistency = (
    match_stats.groupby(KEYS)
    .agg(
        evaluated_matches=("match_id", "nunique"),
        success_rate=("successful", "mean"),
        median_pressure_sr=("match_sr", "median"),
        pressure_sr_std=("match_sr", "std")
    )
    .reset_index()
)

result = result.merge(
    consistency,
    on=KEYS,
    how="left"
)

# -----------------------------------
# 5. MINIMUM SAMPLE REQUIREMENTS
# -----------------------------------

result["eligible"] = (
    (result["balls_normal"] >= 30)
    & (result["balls_pressure"] >= 30)
    & (result["matches_normal"] >= 3)
    & (result["matches_pressure"] >= 3)
    & (result["evaluated_matches"] >= 3)
)

result.to_csv(
    OUT / "batting_pri_all.csv",
    index=False
)

eligible = result[result["eligible"]].copy()

# -----------------------------------
# 6. PERCENTILE NORMALISATION
# -----------------------------------

# Compare players within their format and phase
GROUP = ["match_format", "phase"]

def percentile(column, ascending=True):
    return (
        eligible.groupby(GROUP)[column]
        .rank(pct=True, ascending=ascending)
        * 100
    )

eligible["sr_improvement_score"] = percentile(
    "sr_improvement"
)

eligible["dismissal_improvement_score"] = percentile(
    "dismissal_improvement"
)

eligible["pressure_sr_score"] = percentile(
    "sr_pressure"
)

eligible["consistency_score"] = percentile(
    "success_rate"
)

eligible["survival_score"] = percentile(
    "dismissal_rate_pressure",
    ascending=False
)

eligible["peer_group_size"] = (
    eligible.groupby(GROUP)["striker_id"]
    .transform("size")
)

# -----------------------------------
# 7. WEIGHTED PRI
# -----------------------------------

eligible["raw_pri"] = (
    0.30 * eligible["sr_improvement_score"]
    + 0.25 * eligible["dismissal_improvement_score"]
    + 0.20 * eligible["pressure_sr_score"]
    + 0.15 * eligible["consistency_score"]
    + 0.10 * eligible["survival_score"]
)

# -----------------------------------
# 8. SAMPLE-SIZE ADJUSTMENT
# -----------------------------------

# Harmonic mean gives importance to both
# normal and pressure sample sizes.

eligible["effective_sample"] = (
    2 * eligible["balls_normal"]
    * eligible["balls_pressure"]
    / (
        eligible["balls_normal"]
        + eligible["balls_pressure"]
    )
)

eligible["confidence_factor"] = (
    eligible["effective_sample"]
    / (eligible["effective_sample"] + 50)
)

# Shrink uncertain scores towards neutral (50)

eligible["batting_pri"] = (
    50 + eligible["confidence_factor"]
    * (eligible["raw_pri"] - 50)
)

# -----------------------------------
# 9. SORT AND SAVE
# -----------------------------------

eligible = eligible.sort_values(
    "batting_pri",
    ascending=False
)

eligible.to_csv(
    OUT / "batting_pri_ranked.csv",
    index=False
)

# -----------------------------------
# 10. DISPLAY RESULTS
# -----------------------------------

print("\n=== BATTING PRI ANALYSIS ===")

print("Total comparisons:", len(result))
print("Eligible comparisons:", len(eligible))
print("Eligible players:", eligible["striker_id"].nunique())

print("\n=== ELIGIBLE COMPARISONS BY PHASE ===")
print(eligible["phase"].value_counts())

print("\n=== PEER GROUP SIZES ===")
print(eligible.groupby(GROUP).size())

print("\n=== TOP 20 BATTING PRI COMPARISONS ===")

columns = [
    "striker_name",
    "match_format",
    "phase",
    "balls_normal",
    "balls_pressure",
    "sr_normal",
    "sr_pressure",
    "sr_improvement",
    "dismissal_improvement",
    "success_rate",
    "batting_pri"
]

print(
    eligible[columns]
    .head(20)
    .round(2)
    .to_string(index=False)
)

print("\nSaved results to:", OUT)
