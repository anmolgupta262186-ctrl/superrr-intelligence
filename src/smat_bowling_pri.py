
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/domestic/smat")
OUT = BASE / "pri"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE / "smat_pressure_deliveries.csv",
    low_memory=False
)

# ------------------------------------
# 1. CONFIGURATION
# ------------------------------------

KEYS = [
    "bowler_id",
    "bowler_name",
    "league",
    "phase"
]

GROUP = ["league", "phase"]

MIN_BASELINE_BALLS = 30
MIN_PRESSURE_BALLS = 24
MIN_MATCHES = 3
MIN_PEERS = 5
SHRINKAGE = 50

df = df[
    df["bowling_pressure_category"].isin(
        ["Normal", "Moderate", "High"]
    )
].copy()

df["condition"] = df["bowling_pressure_category"]

# ------------------------------------
# 2. AGGREGATE BOWLING PERFORMANCE
# ------------------------------------

stats = (
    df.groupby(KEYS + ["condition"])
    .agg(
        runs=("bowler_runs", "sum"),
        balls=("is_legal", "sum"),
        wickets=("bowler_wicket", "sum"),
        dots=("is_dot_bowl", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

stats = stats[stats["balls"] > 0].copy()

stats["economy"] = (
    6 * stats["runs"] / stats["balls"]
)

stats["wicket_rate"] = (
    100 * stats["wickets"] / stats["balls"]
)

stats["dot_pct"] = (
    100 * stats["dots"] / stats["balls"]
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
        runs=("bowler_runs", "sum"),
        balls=("is_legal", "sum"),
        wickets=("bowler_wicket", "sum")
    )
    .reset_index()
)

match_stats = match_stats[
    match_stats["balls"] >= 6
].copy()

match_stats["match_economy"] = (
    6 * match_stats["runs"]
    / match_stats["balls"]
)

match_stats["match_wicket_rate"] = (
    100 * match_stats["wickets"]
    / match_stats["balls"]
)

# ------------------------------------
# 4. PRESSURE COMPARISON
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

    result["economy_improvement"] = (
        result["economy_baseline"]
        - result["economy_pressure"]
    )

    result["wicket_rate_improvement"] = (
        result["wicket_rate_pressure"]
        - result["wicket_rate_baseline"]
    )

    result["dot_pct_improvement"] = (
        result["dot_pct_pressure"]
        - result["dot_pct_baseline"]
    )

    # --------------------------------
    # 5. CONSISTENCY
    # --------------------------------

    consistency_data = match_stats.merge(
        baseline[
            KEYS + ["economy", "wicket_rate"]
        ],
        on=KEYS,
        how="inner"
    )

    consistency_data["economy_success"] = (
        consistency_data["match_economy"]
        <= consistency_data["economy"]
    ).astype(int)

    consistency_data["wicket_success"] = (
        consistency_data["match_wicket_rate"]
        >= consistency_data["wicket_rate"]
    ).astype(int)

    consistency_data["success"] = (
        0.5 * consistency_data["economy_success"]
        + 0.5 * consistency_data["wicket_success"]
    )

    consistency = (
        consistency_data.groupby(KEYS)
        .agg(
            evaluated_matches=("match_id", "nunique"),
            success_rate=("success", "mean"),
            median_pressure_economy=(
                "match_economy", "median"
            ),
            pressure_economy_std=(
                "match_economy", "std"
            )
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
        OUT / f"external_bowling_{baseline_category.lower()}_all.csv",
        index=False
    )

    eligible = result[result["eligible"]].copy()

    eligible["peer_group_size"] = (
        eligible.groupby(GROUP)["bowler_id"]
        .transform("nunique")
    )

    insufficient = eligible[
        eligible["peer_group_size"] < MIN_PEERS
    ]

    insufficient.to_csv(
        OUT / f"bowling_{baseline_category.lower()}_insufficient_peers.csv",
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

    eligible["economy_improvement_score"] = percentile(
        "economy_improvement"
    )

    eligible["wicket_improvement_score"] = percentile(
        "wicket_rate_improvement"
    )

    eligible["pressure_economy_score"] = percentile(
        "economy_pressure",
        ascending=False
    )

    eligible["consistency_score"] = percentile(
        "success_rate"
    )

    eligible["pressure_wicket_score"] = percentile(
        "wicket_rate_pressure"
    )

    # --------------------------------
    # 8. WEIGHTED PRI
    # --------------------------------

    eligible["raw_pri"] = (
        0.30 * eligible["economy_improvement_score"]
        + 0.25 * eligible["wicket_improvement_score"]
        + 0.20 * eligible["pressure_economy_score"]
        + 0.15 * eligible["consistency_score"]
        + 0.10 * eligible["pressure_wicket_score"]
    )

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

    eligible["bowling_pri"] = (
        50 + eligible["confidence_factor"]
        * (eligible["raw_pri"] - 50)
    )

    return eligible.sort_values(
        "bowling_pri",
        ascending=False
    )

# ------------------------------------
# 9. CALCULATE BOTH BASELINES
# ------------------------------------

normal_pri = calculate_pri("Normal")
moderate_pri = calculate_pri("Moderate")

normal_pri.to_csv(
    OUT / "external_bowling_pri_normal.csv",
    index=False
)

moderate_pri.to_csv(
    OUT / "external_bowling_pri_moderate.csv",
    index=False
)

combined = pd.concat(
    [normal_pri, moderate_pri],
    ignore_index=True
)

combined.to_csv(
    OUT / "external_bowling_pri_ranked.csv",
    index=False
)

# ------------------------------------
# 10. PHASE-SPECIFIC WATCHLISTS
# ------------------------------------

for phase in ["Powerplay", "Middle", "Death"]:

    specialists = combined[
        combined["phase"] == phase
    ].sort_values(
        ["baseline_category", "bowling_pri"],
        ascending=[True, False]
    )

    specialists.to_csv(
        OUT / f"external_{phase.lower()}_bowling_candidates.csv",
        index=False
    )

# ------------------------------------
# 11. DISPLAY RESULTS
# ------------------------------------

columns = [
    "bowler_name",
    "league",
    "phase",
    "baseline_category",
    "balls_pressure",
    "economy_baseline",
    "economy_pressure",
    "economy_improvement",
    "wicket_rate_improvement",
    "bowling_pri"
]

for label, data in [
    ("NORMAL VS HIGH", normal_pri),
    ("MODERATE VS HIGH", moderate_pri)
]:

    print(f"\n=== {label} ===")
    print("Eligible comparisons:", len(data))
    print("Unique players:", data["bowler_id"].nunique())

    print(
        data[columns].head(15)
        .round(2).to_string(index=False)
    )

    for phase in ["Powerplay", "Middle", "Death"]:

        print(f"\n=== {phase.upper()} SPECIALISTS ===")

        print(
            data[data["phase"] == phase][columns]
            .head(10)
            .round(2)
            .to_string(index=False)
        )

print("\n=== EXTERNAL BOWLING PRI SUMMARY ===")

print("Total ranked comparisons:", len(combined))
print("Unique ranked bowlers:", combined["bowler_id"].nunique())

print("\n=== COVERAGE BY LEAGUE ===")

print(pd.crosstab(
    combined["league"],
    combined["baseline_category"]
))

print("\nSaved results to:", OUT)
