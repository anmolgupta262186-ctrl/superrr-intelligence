
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/external")
OUT = BASE / "pri"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE / "external_pressure_deliveries.csv",
    low_memory=False
)

# ------------------------------------
# 1. CONFIGURATION
# ------------------------------------

KEYS = [
    "striker_id",
    "striker_name",
    "league",
    "phase",
    "batting_role"
]

GROUP = [
    "league",
    "phase",
    "batting_role"
]

MIN_BASELINE_BALLS = 30
MIN_PRESSURE_BALLS = 30
MIN_MATCHES = 3
MIN_PEERS = 5
SHRINKAGE = 50

df = df[
    df["batting_pressure_category"].isin(
        ["Normal", "Moderate", "High"]
    )
].copy()

df["condition"] = df["batting_pressure_category"]

# ------------------------------------
# 2. AGGREGATE PERFORMANCE
# ------------------------------------

stats = (
    df.groupby(KEYS + ["condition"])
    .agg(
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum"),
        dismissals=("striker_dismissal", "sum"),
        dots=("is_dot_bat", "sum"),
        boundaries=("is_boundary", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

stats = stats[stats["balls"] > 0].copy()

stats["sr"] = 100 * stats["runs"] / stats["balls"]

stats["dismissal_rate"] = (
    100 * stats["dismissals"] / stats["balls"]
)

stats["dot_pct"] = (
    100 * stats["dots"] / stats["balls"]
)

stats["boundary_pct"] = (
    100 * stats["boundaries"] / stats["balls"]
)

# ------------------------------------
# 3. PRESSURE MATCH PERFORMANCE
# ------------------------------------

pressure = stats[
    stats["condition"] == "High"
].drop(columns="condition")

pressure_df = df[df["condition"] == "High"]

match_stats = (
    pressure_df.groupby(KEYS + ["match_id"])
    .agg(
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum")
    )
    .reset_index()
)

match_stats = match_stats[
    match_stats["balls"] >= 6
].copy()

match_stats["match_sr"] = (
    100 * match_stats["runs"]
    / match_stats["balls"]
)

# ------------------------------------
# 4. PRESSURE COMPARISON FUNCTION
# ------------------------------------

def calculate_pri(baseline_category):

    baseline = stats[
        stats["condition"] == baseline_category
    ].drop(columns="condition")

    result = baseline.merge(
        pressure,
        on=KEYS,
        suffixes=("_baseline", "_pressure")
    )

    result["baseline_category"] = baseline_category

    result["sr_improvement"] = (
        result["sr_pressure"]
        - result["sr_baseline"]
    )

    result["dismissal_improvement"] = (
        result["dismissal_rate_baseline"]
        - result["dismissal_rate_pressure"]
    )

    result["dot_pct_improvement"] = (
        result["dot_pct_baseline"]
        - result["dot_pct_pressure"]
    )

    result["boundary_pct_improvement"] = (
        result["boundary_pct_pressure"]
        - result["boundary_pct_baseline"]
    )

    # --------------------------------
    # 5. MATCH CONSISTENCY
    # --------------------------------

    consistency_data = match_stats.merge(
        baseline[KEYS + ["sr"]],
        on=KEYS,
        how="inner"
    )

    consistency_data["successful"] = (
        consistency_data["match_sr"]
        >= consistency_data["sr"]
    ).astype(int)

    consistency = (
        consistency_data.groupby(KEYS)
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

    # --------------------------------
    # 6. SAMPLE REQUIREMENTS
    # --------------------------------

    result["eligible"] = (
        (result["balls_baseline"] >= MIN_BASELINE_BALLS)
        & (result["balls_pressure"] >= MIN_PRESSURE_BALLS)
        & (result["matches_baseline"] >= MIN_MATCHES)
        & (result["matches_pressure"] >= MIN_MATCHES)
        & (result["evaluated_matches"] >= MIN_MATCHES)
    )

    result.to_csv(
        OUT / f"external_batting_{baseline_category.lower()}_all.csv",
        index=False
    )

    eligible = result[result["eligible"]].copy()

    eligible["peer_group_size"] = (
        eligible.groupby(GROUP)["striker_id"]
        .transform("nunique")
    )

    insufficient = eligible[
        eligible["peer_group_size"] < MIN_PEERS
    ].copy()

    insufficient.to_csv(
        OUT / f"batting_{baseline_category.lower()}_insufficient_peers.csv",
        index=False
    )

    eligible = eligible[
        eligible["peer_group_size"] >= MIN_PEERS
    ].copy()

    # --------------------------------
    # 7. PERCENTILE NORMALISATION
    # --------------------------------

    def percentile(column, ascending=True):

        rank = (
            eligible.groupby(GROUP)[column]
            .rank(
                method="average",
                ascending=ascending
            )
        )

        size = (
            eligible.groupby(GROUP)[column]
            .transform("count")
        )

        return 100 * (rank - 1) / (size - 1)

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

    # --------------------------------
    # 8. WEIGHTED PRI
    # --------------------------------

    eligible["raw_pri"] = (
        0.30 * eligible["sr_improvement_score"]
        + 0.25 * eligible["dismissal_improvement_score"]
        + 0.20 * eligible["pressure_sr_score"]
        + 0.15 * eligible["consistency_score"]
        + 0.10 * eligible["survival_score"]
    )

    # Sample-size adjustment

    eligible["effective_sample"] = (
        2 * eligible["balls_baseline"]
        * eligible["balls_pressure"]
        / (
            eligible["balls_baseline"]
            + eligible["balls_pressure"]
        )
    )

    eligible["confidence_factor"] = (
        eligible["effective_sample"]
        / (eligible["effective_sample"] + SHRINKAGE)
    )

    eligible["batting_pri"] = (
        50 + eligible["confidence_factor"]
        * (eligible["raw_pri"] - 50)
    )

    return eligible.sort_values(
        "batting_pri",
        ascending=False
    )

# ------------------------------------
# 9. CALCULATE BOTH COMPARISONS
# ------------------------------------

normal_pri = calculate_pri("Normal")
moderate_pri = calculate_pri("Moderate")

normal_pri.to_csv(
    OUT / "external_batting_pri_normal.csv",
    index=False
)

moderate_pri.to_csv(
    OUT / "external_batting_pri_moderate.csv",
    index=False
)

combined = pd.concat(
    [normal_pri, moderate_pri],
    ignore_index=True
)

combined.to_csv(
    OUT / "external_batting_pri_ranked.csv",
    index=False
)

# ------------------------------------
# 10. RR ROLE-SPECIFIC WATCHLISTS
# ------------------------------------

middle_order = combined[
    combined["batting_role"] == "Middle Order"
]

finishers = combined[
    (combined["batting_role"].isin(
        ["Middle Order", "Lower Middle Order"]
    ))
    & (combined["phase"] == "Death")
]

middle_order.to_csv(
    OUT / "external_middle_order_candidates.csv",
    index=False
)

finishers.to_csv(
    OUT / "external_finisher_candidates.csv",
    index=False
)

# ------------------------------------
# 11. DISPLAY RESULTS
# ------------------------------------

columns = [
    "striker_name",
    "league",
    "phase",
    "batting_role",
    "baseline_category",
    "balls_pressure",
    "sr_baseline",
    "sr_pressure",
    "batting_pri"
]

for name, data in [
    ("NORMAL VS HIGH", normal_pri),
    ("MODERATE VS HIGH", moderate_pri)
]:

    print(f"\n=== {name} ===")

    print("Eligible comparisons:", len(data))
    print("Unique players:", data["striker_id"].nunique())

    print("\nTOP 15:")

    print(
        data[columns].head(15)
        .round(2).to_string(index=False)
    )

for category in ["Normal", "Moderate"]:

    print(f"\n=== MIDDLE ORDER: {category} BASELINE ===")

    print(
        middle_order[
            middle_order["baseline_category"] == category
        ][columns]
        .sort_values("batting_pri", ascending=False)
        .head(15).round(2).to_string(index=False)
    )

    print(f"\n=== FINISHERS: {category} BASELINE ===")

    print(
        finishers[
            finishers["baseline_category"] == category
        ][columns]
        .sort_values("batting_pri", ascending=False)
        .head(15).round(2).to_string(index=False)
    )

print("\n=== EXTERNAL BATTING PRI SUMMARY ===")

print("Total ranked comparisons:", len(combined))
print("Unique ranked batters:", combined["striker_id"].nunique())

print("\n=== COVERAGE BY LEAGUE ===")
print(pd.crosstab(
    combined["league"],
    combined["baseline_category"]
))

print("\nSaved results to:", OUT)
