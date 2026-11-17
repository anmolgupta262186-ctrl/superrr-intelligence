
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/auction2027")
OUT = BASE / "pressure_audit"

OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD ALL SCOUTING PLAYERS
# ------------------------------------

df = pd.read_csv(
    BASE / "whi/complete_whi_analysis.csv",
    low_memory=False
)

numeric_columns = [
    "pri", "whi", "rri",
    "balls_normal", "balls_baseline",
    "balls_pressure",
    "matches_normal", "matches_baseline",
    "matches_pressure",
    "sr_normal", "sr_baseline", "sr_pressure",
    "dismissal_rate_normal",
    "dismissal_rate_baseline",
    "dismissal_rate_pressure",
    "run_rate_normal", "run_rate_pressure",
    "economy_baseline", "economy_pressure",
    "wicket_rate_normal", "wicket_rate_baseline",
    "wicket_rate_pressure",
    "success_rate", "evaluated_matches",
    "boundary_pct_baseline",
    "boundary_pct_pressure",
    "dot_pct_baseline", "dot_pct_pressure"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col], errors="coerce"
    )

# ------------------------------------
# 2. BASELINE PERFORMANCE
# ------------------------------------

df["baseline_balls"] = df[
    "balls_baseline"
].combine_first(df["balls_normal"])

df["baseline_matches"] = df[
    "matches_baseline"
].combine_first(df["matches_normal"])

df["baseline_sr"] = df[
    "sr_baseline"
].combine_first(df["sr_normal"])

df["baseline_dismissal_rate"] = df[
    "dismissal_rate_baseline"
].combine_first(df["dismissal_rate_normal"])

df["baseline_wicket_rate"] = df[
    "wicket_rate_baseline"
].combine_first(df["wicket_rate_normal"])

df["baseline_run_control"] = df[
    "economy_baseline"
].combine_first(df["run_rate_normal"])

df["pressure_run_control"] = df[
    "economy_pressure"
].combine_first(df["run_rate_pressure"])

# ------------------------------------
# 3. BATTING PRESSURE IMPROVEMENT
# ------------------------------------

df["strike_rate_change"] = (
    df["sr_pressure"] - df["baseline_sr"]
)

df["dismissal_control_change"] = (
    df["baseline_dismissal_rate"]
    - df["dismissal_rate_pressure"]
)

df["boundary_change"] = (
    df["boundary_pct_pressure"]
    - df["boundary_pct_baseline"]
)

# ------------------------------------
# 4. BOWLING PRESSURE IMPROVEMENT
# ------------------------------------

df["run_control_change"] = (
    df["baseline_run_control"]
    - df["pressure_run_control"]
)

df["wicket_rate_change"] = (
    df["wicket_rate_pressure"]
    - df["baseline_wicket_rate"]
)

df["dot_ball_change"] = np.where(
    df["skill"] == "Batting",

    df["dot_pct_baseline"]
    - df["dot_pct_pressure"],

    df["dot_pct_pressure"]
    - df["dot_pct_baseline"]
)

# Positive changes indicate improvement.

# ------------------------------------
# 5. EVIDENCE STRENGTH
# ------------------------------------

def evidence_strength(row):

    required = [
        "balls_pressure",
        "baseline_balls",
        "matches_pressure",
        "baseline_matches",
        "evaluated_matches"
    ]

    if any(pd.isna(row[c]) for c in required):
        return "Incomplete evidence"

    if (
        row["balls_pressure"] >= 100
        and row["baseline_balls"] >= 100
        and row["matches_pressure"] >= 5
        and row["baseline_matches"] >= 5
        and row["evaluated_matches"] >= 5
    ):
        return "Strong"

    minimum = (
        30 if row["skill"] == "Batting"
        else 24
    )

    if (
        row["balls_pressure"] >= minimum
        and row["baseline_balls"] >= 30
        and row["matches_pressure"] >= 3
        and row["baseline_matches"] >= 3
        and row["evaluated_matches"] >= 3
    ):
        return "Moderate"

    return "Limited"


df["audit_evidence_strength"] = df.apply(
    evidence_strength, axis=1
)

# ------------------------------------
# 6. PRESSURE RESPONSE CLASSIFICATION
# ------------------------------------

def pressure_response(row):

    if row["skill"] == "Batting":

        first = row["strike_rate_change"]

        second = row["dismissal_control_change"]

    else:

        first = row["run_control_change"]

        second = row["wicket_rate_change"]

    if pd.isna(first) or pd.isna(second):
        return "Insufficient metrics"

    if first > 0 and second > 0:
        return "Improves in both metrics"

    if first < 0 and second < 0:
        return "Declines in both metrics"

    if first == 0 and second == 0:
        return "Maintains performance"

    if first >= 0 and second >= 0:
        return "Improves without decline"

    if first <= 0 and second <= 0:
        return "Declines without improvement"

    return "Mixed pressure response"


df["pressure_response"] = df.apply(
    pressure_response, axis=1
)

# ------------------------------------
# 7. PRESSURE RELIABILITY REVIEW
# ------------------------------------

def audit_status(row):

    if pd.isna(row["pri"]):
        return "PRI unavailable"

    if row["audit_evidence_strength"] in [
        "Limited",
        "Incomplete evidence"
    ]:
        return "Requires additional evidence"

    if row["pressure_response"] == (
        "Insufficient metrics"
    ):
        return "Requires additional evidence"

    if (
        row["pri"] >= 65
        and row["pressure_response"] in [
            "Improves in both metrics",
            "Improves without decline"
        ]
    ):
        return "Strong positive pressure signal"

    if row["pressure_response"] in [
        "Declines in both metrics",
        "Declines without improvement"
    ]:
        return "Pressure decline - review"

    return "Evaluated - mixed or moderate signal"


df["pressure_audit_status"] = df.apply(
    audit_status, axis=1
)

# ------------------------------------
# 8. SAVE ALL PERFORMANCE EVIDENCE
# ------------------------------------

df = df.sort_values(
    ["pri", "balls_pressure"],
    ascending=[False, False]
)

df.to_csv(
    OUT / "complete_pressure_audit.csv",
    index=False
)

# ------------------------------------
# 9. INDIVIDUAL PLAYER AUDIT
# ------------------------------------

summary = df.groupby(
    "name_key", as_index=False
).agg(
    player_name=("canonical_name", "first"),

    roles=("target_role",
           lambda x: ", ".join(sorted(set(x)))),

    competitions=("competition",
                  lambda x: ", ".join(sorted(set(x)))),

    performance_records=("pri", "size"),

    highest_observed_pri=("pri", "max"),

    lowest_observed_pri=("pri", "min"),

    positive_pressure_records=(
        "pressure_audit_status",
        lambda x: (
            x == "Strong positive pressure signal"
        ).sum()
    ),

    pressure_decline_records=(
        "pressure_audit_status",
        lambda x: (
            x == "Pressure decline - review"
        ).sum()
    ),

    strong_evidence_records=(
        "audit_evidence_strength",
        lambda x: (x == "Strong").sum()
    ),

    qualifying_evidence_records=(
        "audit_evidence_strength",
        lambda x: x.isin(
            ["Strong", "Moderate"]
        ).sum()
    )
)

summary["player_audit_status"] = np.select(
    [
        summary["qualifying_evidence_records"] == 0,

        (
            (summary["positive_pressure_records"] > 0)
            & (summary["pressure_decline_records"] > 0)
        ),

        summary["positive_pressure_records"] > 0,

        summary["pressure_decline_records"] > 0
    ],
    [
        "Insufficient evidence",
        "Situation-dependent response",
        "Positive pressure evidence",
        "Pressure decline observed"
    ],
    default="Mixed or moderate evidence"
)

summary = summary.sort_values(
    "highest_observed_pri",
    ascending=False
)

summary.to_csv(
    OUT / "individual_player_pressure_report.csv",
    index=False
)

# ------------------------------------
# 10. SEPARATE COMPARISON TYPES
# ------------------------------------

for baseline in ["Normal", "Moderate"]:

    data = df[
        df["baseline_category"] == baseline
    ]

    for skill in ["Batting", "Bowling"]:

        records = data[data["skill"] == skill]

        records.to_csv(
            OUT / (
                f"{skill.lower()}_"
                f"{baseline.lower()}_pressure.csv"
            ),
            index=False
        )

# ------------------------------------
# 11. PRESERVE DOMESTIC PROSPECTS
# ------------------------------------

for skill in ["batting", "bowling"]:

    domestic = pd.read_csv(
        BASE / "global_rankings"
        / f"domestic_{skill}_prospects.csv"
    )

    domestic["audit_note"] = (
        "Absolute pressure watchlist; "
        "baseline comparison requires verification"
    )

    domestic.to_csv(
        OUT / f"domestic_{skill}_pressure_review.csv",
        index=False
    )

# ------------------------------------
# 12. FINAL SUMMARY
# ------------------------------------

print("\n=== COMPREHENSIVE PRESSURE AUDIT ===")

print("Total performance records:", len(df))

print("Unique players audited:",
      summary["name_key"].nunique())

print("\n=== EVIDENCE STRENGTH ===")
print(df["audit_evidence_strength"].value_counts())

print("\n=== PRESSURE RESPONSE ===")
print(df["pressure_response"].value_counts())

print("\n=== INDIVIDUAL PLAYER CLASSIFICATION ===")
print(summary["player_audit_status"].value_counts())

print("\n=== TOP 30 PRESSURE PROSPECTS ===")

print(summary[[
    "player_name",
    "highest_observed_pri",
    "positive_pressure_records",
    "pressure_decline_records",
    "player_audit_status"
]].head(30).round(2).to_string(index=False))

print("\nSaved results to:", OUT)
