
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/rr_official")
OUT = Path("data/processed/official")
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD DATA
# ------------------------------------

balls = pd.read_csv(
    RAW / "ball_by_ball.csv",
    low_memory=False
)

matches = pd.read_csv(
    RAW / "matches.csv",
    low_memory=False
)

competitions = pd.read_csv(
    RAW / "competitions.csv",
    dtype={"season": str}
)

print("Loaded deliveries:", len(balls))

# ------------------------------------
# 2. KEEP REGULATION INNINGS
# ------------------------------------

super_over_balls = balls[balls["innings"] > 2]

balls = balls[balls["innings"].isin([1, 2])].copy()

print("Excluded Super Over deliveries:", len(super_over_balls))

# ------------------------------------
# 3. CLASSIFY PHASES
# ------------------------------------

def get_phase(over):
    if 1 <= over <= 6:
        return "Powerplay"
    elif 7 <= over <= 15:
        return "Middle"
    elif 16 <= over <= 20:
        return "Death"
    return "Unknown"

balls["phase"] = balls["overid"].apply(get_phase)

# ------------------------------------
# 4. IDENTIFY LEGAL DELIVERIES
# ------------------------------------

# 'other' classified as illegal based on
# internal dataset validation.

ILLEGAL_DELIVERIES = [
    "wide",
    "Overstep",
    "other"
]

balls["is_legal"] = (
    ~balls["extras_type"].isin(ILLEGAL_DELIVERIES)
).astype(int)

# Batter balls faced
# Preserve existing convention until the
# exact definition of 'other' is confirmed.

balls["batter_ball"] = (
    balls["extras_type"] != "wide"
).astype(int)

# Flag uncertain extras category
balls["other_extras_flag"] = (
    balls["extras_type"] == "other"
).astype(int)

# ------------------------------------
# 5. BASIC BATTING METRICS
# ------------------------------------

balls["batter_runs"] = balls["runs"]

balls["is_dot_bat"] = (
    (balls["batter_runs"] == 0) &
    (balls["batter_ball"] == 1)
).astype(int)

balls["is_boundary"] = (
    balls["is_four"].fillna(False) |
    balls["is_six"].fillna(False)
).astype(int)

# ------------------------------------
# 6. WICKET CLASSIFICATION
# ------------------------------------

BOWLER_WICKETS = {
    "Caught",
    "Bowled",
    "LBW",
    "Stump",
    "Hit Wicket"
}

balls["bowler_wicket"] = (
    balls["dismissal_type"]
    .fillna("")
    .isin(BOWLER_WICKETS)
).astype(int)

balls["team_wicket"] = (
    balls["is_wicket"].fillna(False)
).astype(int)

# ------------------------------------
# 7. MATCH AND COMPETITION CONTEXT
# ------------------------------------

match_columns = [
    "match_id",
    "comp_id",
    "match_date",
    "venue_country",
    "first_inn_revised_overs",
    "second_inn_revised_overs",
    "revised_target",
    "win_team_id",
    "result"
]

balls = balls.merge(
    matches[match_columns],
    on="match_id",
    how="left",
    validate="many_to_one"
)

balls = balls.merge(
    competitions[
        ["comp_id", "comp_name", "match_format", "season"]
    ],
    on="comp_id",
    how="left",
    validate="many_to_one"
)

# ------------------------------------
# 8. LEGAL BALL VALIDATION
# ------------------------------------

over_check = (
    balls.groupby(
        ["match_id", "innings", "overid"],
        as_index=False
    )
    .agg(
        legal_balls=("is_legal", "sum")
    )
)

innings_check = (
    balls.groupby(
        ["match_id", "innings"],
        as_index=False
    )
    .agg(
        legal_balls=("is_legal", "sum")
    )
)

# Flag unusual overs
over_check["unusual_over"] = (
    over_check["legal_balls"] > 6
).astype(int)

balls = balls.merge(
    over_check[
        ["match_id", "innings", "overid", "unusual_over"]
    ],
    on=["match_id", "innings", "overid"],
    how="left",
    validate="many_to_one"
)

# ------------------------------------
# 9. VALIDATION OUTPUT
# ------------------------------------

print("\n=== PREPROCESSING VALIDATION ===")

print("Remaining deliveries:", len(balls))
print("Matches:", balls["match_id"].nunique())
print("Players batting:", balls["striker_id"].nunique())
print("Players bowling:", balls["bowler_id"].nunique())

print("\nLegal deliveries:", balls["is_legal"].sum())
print("Illegal deliveries:", (balls["is_legal"] == 0).sum())
print("Batter balls faced:", balls["batter_ball"].sum())
print("Bowler wickets:", balls["bowler_wicket"].sum())

print("\nMissing match information:",
      balls["comp_id"].isna().sum())

print("Unknown phases:",
      (balls["phase"] == "Unknown").sum())

print("\n=== LEGAL BALL QUALITY CHECK ===")

print(
    "Other extras deliveries:",
    balls["other_extras_flag"].sum()
)

print(
    "Overs exceeding 6 legal balls:",
    (over_check["legal_balls"] > 6).sum()
)

print(
    "Innings exceeding 120 legal balls:",
    (innings_check["legal_balls"] > 120).sum()
)

print("\n=== UNUSUAL OVERS ===")

print(
    over_check[
        over_check["legal_balls"] > 6
    ].to_string(index=False)
)

# ------------------------------------
# 10. SAVE CLEAN DATA
# ------------------------------------

output_file = OUT / "clean_deliveries.csv"

balls.to_csv(output_file, index=False)

print("\nSaved cleaned data to:", output_file)
