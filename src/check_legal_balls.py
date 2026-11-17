
import pandas as pd
from pathlib import Path

BASE = Path("data/raw/rr_official")

df = pd.read_csv(
    BASE / "ball_by_ball.csv",
    low_memory=False
)

df = df[df["innings"].isin([1, 2])].copy()

df["is_legal"] = (
    ~df["extras_type"].isin(["wide", "Overstep"])
).astype(int)

# Count legal balls in each innings
innings = (
    df.groupby(["match_id", "innings"])
    .agg(
        legal_balls=("is_legal", "sum"),
        deliveries=("match_id", "size")
    )
    .reset_index()
)

invalid = innings[innings["legal_balls"] > 120]

print("\n=== INNINGS EXCEEDING 120 BALLS ===")
print("Total:", len(invalid))

print("\nLegal ball distribution:")
print(
    invalid["legal_balls"]
    .value_counts()
    .sort_index()
)

# Inspect over-level patterns
problem_ids = invalid[
    ["match_id", "innings"]
]

problem_balls = df.merge(
    problem_ids,
    on=["match_id", "innings"],
    how="inner"
)

print("\n=== EXTRAS IN FLAGGED INNINGS ===")
print(
    problem_balls["extras_type"]
    .value_counts(dropna=False)
)

print("\n=== LEGAL BALLS PER OVER ===")

over_counts = (
    problem_balls.groupby(
        ["match_id", "innings", "overid"]
    )["is_legal"]
    .sum()
    .reset_index(name="legal_balls")
)

print(
    over_counts["legal_balls"]
    .value_counts()
    .sort_index()
)

print("\n=== OVERS EXCEEDING SIX LEGAL BALLS ===")

extra_overs = over_counts[
    over_counts["legal_balls"] > 6
]

print("Count:", len(extra_overs))
print(extra_overs.head(15).to_string(index=False))

print("\n=== FIRST FIVE FLAGGED INNINGS ===")
print(invalid.head(5).to_string(index=False))
