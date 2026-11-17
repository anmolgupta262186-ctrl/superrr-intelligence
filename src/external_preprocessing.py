
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("data/processed/external")

balls = pd.read_csv(
    BASE / "external_deliveries.csv",
    low_memory=False
)

matches = pd.read_csv(
    BASE / "external_matches.csv",
    low_memory=False
)

# -----------------------------------
# 1. CLASSIFY PHASES
# -----------------------------------

balls["phase"] = np.select(
    [
        balls["overid"].between(1, 6),
        balls["overid"].between(7, 15),
        balls["overid"].between(16, 20)
    ],
    ["Powerplay", "Middle", "Death"],
    default="Unknown"
)

# -----------------------------------
# 2. LEGAL DELIVERIES
# -----------------------------------

balls["is_legal"] = (
    (balls["wides"] == 0)
    & (balls["noballs"] == 0)
).astype(int)

balls["batter_ball"] = (
    balls["wides"] == 0
).astype(int)

# -----------------------------------
# 3. BATTING METRICS
# -----------------------------------

balls["is_dot_bat"] = (
    (balls["batter_runs"] == 0)
    & (balls["batter_ball"] == 1)
).astype(int)

balls["is_four"] = (
    (balls["batter_runs"] == 4)
    & (balls["is_boundary"] == 1)
).astype(int)

balls["is_six"] = (
    (balls["batter_runs"] == 6)
    & (balls["is_boundary"] == 1)
).astype(int)

# Identify striker dismissals

balls["striker_dismissal"] = [
    int(str(player) in str(dismissed).split("|"))
    for player, dismissed in zip(
        balls["striker_id"],
        balls["dismissed_player_ids"]
    )
]

# -----------------------------------
# 4. BOWLING METRICS
# -----------------------------------

# Byes, leg byes and penalty runs
# are not charged to the bowler.

balls["bowler_runs"] = (
    balls["batter_runs"]
    + balls["wides"]
    + balls["noballs"]
)

balls["is_dot_bowl"] = (
    (balls["total_runs"] == 0)
    & (balls["is_legal"] == 1)
).astype(int)

# -----------------------------------
# 5. BATTING ROLES
# -----------------------------------

balls["batting_role"] = np.select(
    [
        balls["batting_order"].between(1, 2),
        balls["batting_order"] == 3,
        balls["batting_order"].between(4, 5),
        balls["batting_order"].between(6, 7),
        balls["batting_order"] >= 8
    ],
    [
        "Opener",
        "Top Order",
        "Middle Order",
        "Lower Middle Order",
        "Lower Order"
    ],
    default="Unknown"
)

# -----------------------------------
# 6. MATCH CONTEXT
# -----------------------------------

context = [
    "match_id",
    "season",
    "scheduled_overs",
    "balls_per_over",
    "match_stage",
    "winner",
    "result",
    "result_method"
]

balls = balls.merge(
    matches[context],
    on="match_id",
    how="left",
    validate="many_to_one"
)

balls["match_format"] = "T20"

# Identify knockout matches

balls["knock_out"] = (
    balls["match_stage"]
    .fillna("")
    .str.lower()
    .str.contains(
        r"final|eliminator|qualifier|knockout",
        regex=True
    )
).astype(int)

# Flag reduced or revised matches

balls["revised_match"] = (
    (balls["scheduled_overs"] != 20)
    | (
        balls["target_overs"].notna()
        & (balls["target_overs"] != 20)
    )
    | balls["result_method"].notna()
)

balls["revised_match"] = (
    balls.groupby("match_id")["revised_match"]
    .transform("max")
)

# -----------------------------------
# 7. DATA QUALITY CHECKS
# -----------------------------------

balls["run_mismatch"] = (
    balls["total_runs"]
    != balls["batter_runs"] + balls["extras_runs"]
)

duplicates = balls.duplicated(
    ["match_id", "innings", "innings_ball_num"]
).sum()

overs = (
    balls.groupby(
        ["match_id", "innings", "overid"]
    )["is_legal"]
    .sum()
)

innings = (
    balls.groupby(
        ["match_id", "innings"]
    )["is_legal"]
    .sum()
)

# -----------------------------------
# 8. SORT AND SAVE
# -----------------------------------

balls = balls.sort_values(
    ["match_id", "innings", "innings_ball_num"]
).reset_index(drop=True)

balls.to_csv(
    BASE / "external_clean_deliveries.csv",
    index=False
)

# -----------------------------------
# 9. VALIDATION OUTPUT
# -----------------------------------

print("\n=== EXTERNAL PREPROCESSING ===")

print("Total deliveries:", len(balls))
print("Matches:", balls["match_id"].nunique())
print("Unique batters:", balls["striker_id"].nunique())
print("Unique bowlers:", balls["bowler_id"].nunique())

print("\n=== DELIVERY STATISTICS ===")

print("Legal balls:", balls["is_legal"].sum())
print("Illegal balls:", (balls["is_legal"] == 0).sum())
print("Batter runs:", balls["batter_runs"].sum())
print("Extras:", balls["extras_runs"].sum())
print("Total runs:", balls["total_runs"].sum())
print("Bowler wickets:", balls["bowler_wicket"].sum())

print("\n=== PHASE DISTRIBUTION ===")
print(balls["phase"].value_counts())

print("\n=== BATTING ROLE DISTRIBUTION ===")
print(balls["batting_role"].value_counts())

print("\n=== MATCH CONTEXT ===")

print(
    "Knockout matches:",
    balls.loc[
        balls["knock_out"] == 1, "match_id"
    ].nunique()
)

print(
    "Revised matches:",
    balls.loc[
        balls["revised_match"], "match_id"
    ].nunique()
)

print("\n=== DATA QUALITY ===")

print("Run mismatches:", balls["run_mismatch"].sum())
print("Duplicate deliveries:", duplicates)
print("Overs exceeding 6 balls:", (overs > 6).sum())
print("Innings exceeding 120 balls:", (innings > 120).sum())

print("\nSaved:", BASE / "external_clean_deliveries.csv")
