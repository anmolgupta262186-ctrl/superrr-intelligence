
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/rr_official")
OUT = Path("data/processed/official/validation")
OUT.mkdir(parents=True, exist_ok=True)

balls = pd.read_csv(
    RAW / "ball_by_ball.csv",
    low_memory=False
)

matches = pd.read_csv(RAW / "matches.csv")

# ---------------------------------
# 1. KEEP REGULATION INNINGS
# ---------------------------------

balls = balls[
    balls["innings"].isin([1, 2])
].copy()

# ---------------------------------
# 2. CLASSIFY EXTRA TYPES
# ---------------------------------

balls["extras_type"] = (
    balls["extras_type"].fillna("none")
)

balls["is_legal"] = (
    ~balls["extras_type"].isin(["wide", "Overstep"])
).astype(int)

# ---------------------------------
# 3. CALCULATE KNOWN RUNS
# ---------------------------------

# Verified batter runs
balls["batter_runs"] = balls["runs"]

# The available fields do not yet establish
# the full extras amount for every delivery.
balls["minimum_known_runs"] = balls["batter_runs"]

# Flag deliveries whose extra-run contribution
# cannot yet be reconstructed reliably.
balls["extras_unresolved"] = (
    balls["extras_type"] != "none"
)

# ---------------------------------
# 4. INNINGS SUMMARY
# ---------------------------------

summary = (
    balls.groupby(
        ["match_id", "innings"],
        as_index=False
    )
    .agg(
        deliveries=("match_id", "size"),
        legal_balls=("is_legal", "sum"),
        batter_runs=("batter_runs", "sum"),
        extras_records=("extras_unresolved", "sum"),
        wickets=("is_wicket", "sum")
    )
)

summary["minimum_known_runs"] = summary["batter_runs"]

summary["overs_bowled"] = (
    summary["legal_balls"] / 6
).round(2)

summary["runs_per_six_legal_balls"] = (
    summary["batter_runs"] * 6 /
    summary["legal_balls"].replace(0, float("nan"))
).round(2)

# ---------------------------------
# 5. ADD MATCH INFORMATION
# ---------------------------------

summary = summary.merge(
    matches[
        [
            "match_id",
            "match_date",
            "first_inn_revised_overs",
            "second_inn_revised_overs",
            "revised_target"
        ]
    ],
    on="match_id",
    how="left",
    validate="many_to_one"
)

summary["revised_match"] = (
    summary[
        [
            "first_inn_revised_overs",
            "second_inn_revised_overs",
            "revised_target"
        ]
    ].notna().any(axis=1)
)

# ---------------------------------
# 6. FLAG POTENTIAL ISSUES
# ---------------------------------

summary["over_120_legal_balls"] = (
    summary["legal_balls"] > 120
)

summary["needs_extras_validation"] = (
    summary["extras_records"] > 0
)

# Check repeated delivery identifiers
duplicate_delivery_ids = balls.duplicated(
    subset=[
        "match_id",
        "innings",
        "innings_ball_num"
    ]
).sum()

# ---------------------------------
# 7. SAVE REPORTS
# ---------------------------------

summary.to_csv(
    OUT / "innings_score_validation.csv",
    index=False
)

issues = summary[
    summary["over_120_legal_balls"] |
    summary["needs_extras_validation"] |
    summary["revised_match"]
]

issues.to_csv(
    OUT / "innings_needing_review.csv",
    index=False
)

# ---------------------------------
# 8. DISPLAY VALIDATION
# ---------------------------------

print("\n=== INNINGS VALIDATION ===")

print("Total regulation deliveries:", len(balls))
print("Matches:", summary["match_id"].nunique())
print("Innings:", len(summary))

print("\n=== RUN STATISTICS ===")
print("Total batter runs:", balls["batter_runs"].sum())
print("Total legal balls:", balls["is_legal"].sum())

print("\n=== EXTRAS ===")
print(
    balls["extras_type"]
    .value_counts()
    .to_string()
)

print("\n=== QUALITY CHECKS ===")

print(
    "Innings with extras records:",
    summary["needs_extras_validation"].sum()
)

print(
    "Innings exceeding 120 legal balls:",
    summary["over_120_legal_balls"].sum()
)

print(
    "Innings from revised matches:",
    summary["revised_match"].sum()
)

print(
    "Duplicate innings-ball identifiers:",
    duplicate_delivery_ids
)

print("\n=== SAMPLE INNINGS SUMMARY ===")

print(
    summary[
        [
            "match_id",
            "innings",
            "legal_balls",
            "batter_runs",
            "extras_records",
            "wickets"
        ]
    ].head(10).to_string(index=False)
)

print("\nReports saved to:", OUT)
