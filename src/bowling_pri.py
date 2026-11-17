
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
    df["bowling_pressure_category"].isin(
        ["Normal", "High"]
    )
].copy()

df["condition"] = df["bowling_pressure_category"]

KEYS = [
    "bowler_id",
    "bowler_name",
    "match_format",
    "phase"
]

# -----------------------------------
# 2. AGGREGATE BOWLING PERFORMANCE
# -----------------------------------

stats = (
    df.groupby(KEYS + ["condition"])
    .agg(
        runs=("batter_runs", "sum"),
        balls=("is_legal", "sum"),
        wickets=("bowler_wicket", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

stats = stats[stats["balls"] > 0].copy()

# Runs conceded off the bat per six legal balls
stats["run_rate"] = (
    6 * stats["runs"] / stats["balls"]
)

# Wickets per 100 legal deliveries
stats["wicket_rate"] = (
    100 * stats["wickets"] / stats["balls"]
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

# Positive improvement is better

result["run_rate_improvement"] = (
    result["run_rate_normal"]
    - result["run_rate_pressure"]
)

result["wicket_rate_improvement"] = (
    result["wicket_rate_pressure"]
    - result["wicket_rate_normal"]
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
        balls=("is_legal", "sum"),
        wickets=("bowler_wicket", "sum")
    )
    .reset_index()
)

match_stats = match_stats[
    match_stats["balls"] >= 6
].copy()

match_stats["match_run_rate"] = (
    6 * match_stats["runs"]
    / match_stats["balls"]
)

match_stats["match_wicket_rate"] = (
    100 * match_stats["wickets"]
    / match_stats["balls"]
)

match_stats = match_stats.merge(
    normal[KEYS + ["run_rate", "wicket_rate"]],
    on=KEYS,
    how="inner"
)

# Compare with individual normal performance

match_stats["run_control_success"] = (
    match_stats["match_run_rate"]
    <= match_stats["run_rate"]
).astype(int)

match_stats["wicket_success"] = (
    match_stats["match_wicket_rate"]
    >= match_stats["wicket_rate"]
).astype(int)

match_stats["success"] = (
    0.5 * match_stats["run_control_success"]
    + 0.5 * match_stats["wicket_success"]
)

consistency = (
    match_stats.groupby(KEYS)
    .agg(
        evaluated_matches=("match_id", "nunique"),
        success_rate=("success", "mean"),
        median_pressure_run_rate=(
            "match_run_rate", "median"
        ),
        pressure_run_rate_std=(
            "match_run_rate", "std"
        )
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
    & (result["balls_pressure"] >= 24)
    & (result["matches_normal"] >= 3)
    & (result["matches_pressure"] >= 3)
    & (result["evaluated_matches"] >= 3)
)

result.to_csv(
    OUT / "bowling_pri_all.csv",
    index=False
)

eligible = result[result["eligible"]].copy()

# -----------------------------------
# 6. PERCENTILE NORMALISATION
# -----------------------------------

GROUP = ["match_format", "phase"]

def percentile(column, ascending=True):
    return (
        eligible.groupby(GROUP)[column]
        .rank(pct=True, ascending=ascending)
        * 100
    )

eligible["run_improvement_score"] = percentile(
    "run_rate_improvement"
)

eligible["wicket_improvement_score"] = percentile(
    "wicket_rate_improvement"
)

eligible["pressure_run_rate_score"] = percentile(
    "run_rate_pressure",
    ascending=False
)

eligible["consistency_score"] = percentile(
    "success_rate"
)

eligible["pressure_wicket_score"] = percentile(
    "wicket_rate_pressure"
)

eligible["peer_group_size"] = (
    eligible.groupby(GROUP)["bowler_id"]
    .transform("size")
)

# -----------------------------------
# 7. WEIGHTED PRI
# -----------------------------------

eligible["raw_pri"] = (
    0.30 * eligible["run_improvement_score"]
    + 0.25 * eligible["wicket_improvement_score"]
    + 0.20 * eligible["pressure_run_rate_score"]
    + 0.15 * eligible["consistency_score"]
    + 0.10 * eligible["pressure_wicket_score"]
)

# -----------------------------------
# 8. SAMPLE-SIZE ADJUSTMENT
# -----------------------------------

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

eligible["bowling_pri"] = (
    50 + eligible["confidence_factor"]
    * (eligible["raw_pri"] - 50)
)

# -----------------------------------
# 9. SORT AND SAVE
# -----------------------------------

eligible = eligible.sort_values(
    "bowling_pri",
    ascending=False
)

eligible.to_csv(
    OUT / "bowling_pri_ranked.csv",
    index=False
)

# -----------------------------------
# 10. DISPLAY RESULTS
# -----------------------------------

print("\n=== BOWLING PRI ANALYSIS ===")

print("Total comparisons:", len(result))
print("Eligible comparisons:", len(eligible))
print("Eligible players:", eligible["bowler_id"].nunique())

print("\n=== ELIGIBLE COMPARISONS BY PHASE ===")
print(eligible["phase"].value_counts())

print("\n=== PEER GROUP SIZES ===")
print(eligible.groupby(GROUP).size())

print("\n=== TOP 20 BOWLING PRI COMPARISONS ===")

columns = [
    "bowler_name",
    "match_format",
    "phase",
    "balls_normal",
    "balls_pressure",
    "run_rate_normal",
    "run_rate_pressure",
    "run_rate_improvement",
    "wicket_rate_improvement",
    "success_rate",
    "bowling_pri"
]

print(
    eligible[columns]
    .head(20)
    .round(2)
    .to_string(index=False)
)

print("\nSaved results to:", OUT)
