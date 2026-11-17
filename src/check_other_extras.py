
from pathlib import Path
import pandas as pd

BASE = Path("data/raw/rr_official")

df = pd.read_csv(
    BASE / "ball_by_ball.csv",
    low_memory=False
)

df = df[df["innings"].isin([1, 2])].copy()

# Current legal-ball definition
df["legal_old"] = (
    ~df["extras_type"].isin(["wide", "Overstep"])
).astype(int)

# Test: treat 'other' as an illegal delivery
df["legal_test"] = (
    ~df["extras_type"].isin(
        ["wide", "Overstep", "other"]
    )
).astype(int)

# Compare over-level counts
GROUP = ["match_id", "innings", "overid"]

overs = (
    df.groupby(GROUP, as_index=False)
    .agg(
        old_legal=("legal_old", "sum"),
        test_legal=("legal_test", "sum"),
        other_count=(
            "extras_type",
            lambda x: (x == "other").sum()
        )
    )
)

print("\n=== OVER VALIDATION ===")

print(
    "Overs above 6 (old):",
    (overs["old_legal"] > 6).sum()
)

print(
    "Overs above 6 (test):",
    (overs["test_legal"] > 6).sum()
)

print(
    "Overs below 6 (test):",
    (overs["test_legal"] < 6).sum()
)

# Compare innings totals
innings = (
    df.groupby(["match_id", "innings"], as_index=False)
    .agg(
        old_legal=("legal_old", "sum"),
        test_legal=("legal_test", "sum")
    )
)

print("\n=== INNINGS VALIDATION ===")

print(
    "Innings above 120 (old):",
    (innings["old_legal"] > 120).sum()
)

print(
    "Innings above 120 (test):",
    (innings["test_legal"] > 120).sum()
)

# Check whether suspicious overs contain 'other'
problem_overs = overs[overs["old_legal"] > 6]

print("\n=== SUSPICIOUS OVERS ===")

print(
    "Overs above 6 containing 'other':",
    (problem_overs["other_count"] > 0).sum()
)

print(
    "Overs above 6 without 'other':",
    (problem_overs["other_count"] == 0).sum()
)

print("\n=== REMAINING PROBLEMS ===")

print(
    overs[overs["test_legal"] > 6]
    .head(15)
    .to_string(index=False)
)

print("\n=== OTHER EXTRAS ===")

print(
    "Total 'other' deliveries:",
    (df["extras_type"] == "other").sum()
)
