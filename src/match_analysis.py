
import json
from pathlib import Path

import pandas as pd

INPUT = Path("data/processed/rr_deliveries_2025_2026.csv")
OUTPUT = Path("data/processed")
RR = "Rajasthan Royals"

(OUTPUT / "overwise").mkdir(parents=True, exist_ok=True)
(OUTPUT / "phasewise").mkdir(parents=True, exist_ok=True)

# ---------------------------------
# 1. LOAD AND PREPROCESS DATA
# ---------------------------------

df = pd.read_csv(INPUT, dtype={"match_id": str})

# Exclude Super Overs (innings 3 and 4)
df = df[df["innings"].isin([1, 2])].copy()

# Identify match phases
df["phase"] = pd.cut(
    df["over"],
    bins=[0, 6, 15, 20],
    labels=["Powerplay", "Middle", "Death"]
)

# Parse extras
df["extras_dict"] = df["extras"].fillna("{}").apply(json.loads)

# Legal balls exclude wides and no-balls
df["is_legal"] = df["extras_dict"].apply(
    lambda x: int("wides" not in x and "noballs" not in x)
)

# Runs charged to bowler exclude byes, legbyes and penalties
df["bowler_runs"] = df.apply(
    lambda r: r["total_runs"]
    - r["extras_dict"].get("byes", 0)
    - r["extras_dict"].get("legbyes", 0)
    - r["extras_dict"].get("penalty", 0),
    axis=1
)

# Dot balls: no runs scored by either team
df["is_dot"] = (df["total_runs"] == 0).astype(int)

# Boundaries scored by batter
df["is_four"] = (df["batter_runs"] == 4).astype(int)
df["is_six"] = (df["batter_runs"] == 6).astype(int)

# Wickets credited to bowler
BOWLER_DISMISSALS = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket"
}

df["bowler_wicket"] = (
    df["dismissal_types"]
    .fillna("")
    .str.split(",")
    .apply(
        lambda kinds: sum(
            kind.strip() in BOWLER_DISMISSALS
            for kind in kinds
        )
    )
)

# ---------------------------------
# 2. IDENTIFY MATCH SITUATION
# ---------------------------------

df["batting_situation"] = df["innings"].map({
    1: "Setting Target",
    2: "Chasing"
})

df["bowling_situation"] = df["innings"].map({
    1: "Bowling First",
    2: "Defending"
})

# Separate RR batting and bowling
bat = df[df["batting_team"] == RR].copy()
bowl = df[df["bowling_team"] == RR].copy()

# ---------------------------------
# 3. RR BATTING OVER-WISE
# ---------------------------------

bat_over = (
    bat.groupby(
        ["season", "match_id", "batting_situation", "over"],
        as_index=False
    )
    .agg(
        runs=("total_runs", "sum"),
        batter_runs=("batter_runs", "sum"),
        wickets=("wicket_count", "sum"),
        legal_balls=("is_legal", "sum"),
        dots=("is_dot", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum")
    )
)

bat_over["run_rate"] = (
    bat_over["runs"] /
    bat_over["legal_balls"].replace(0, float("nan")) * 6
)

bat_over.to_csv(
    OUTPUT / "overwise/rr_batting_overwise.csv",
    index=False
)

# ---------------------------------
# 4. RR BOWLING OVER-WISE
# ---------------------------------

bowl_over = (
    bowl.groupby(
        ["season", "match_id", "bowling_situation", "over"],
        as_index=False
    )
    .agg(
        runs_conceded=("total_runs", "sum"),
        bowler_runs=("bowler_runs", "sum"),
        wickets=("wicket_count", "sum"),
        bowler_wickets=("bowler_wicket", "sum"),
        legal_balls=("is_legal", "sum"),
        dots=("is_dot", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum")
    )
)

bowl_over["economy"] = (
    bowl_over["runs_conceded"] /
    bowl_over["legal_balls"].replace(0, float("nan")) * 6
)

bowl_over["bowler_economy"] = (
    bowl_over["bowler_runs"] /
    bowl_over["legal_balls"].replace(0, float("nan")) * 6
)

bowl_over.to_csv(
    OUTPUT / "overwise/rr_bowling_overwise.csv",
    index=False
)

# ---------------------------------
# 5. RR BATTING PHASE-WISE
# ---------------------------------

bat_phase = (
    bat.groupby(
        ["season", "match_id", "batting_situation", "phase"],
        observed=True,
        as_index=False
    )
    .agg(
        runs=("total_runs", "sum"),
        batter_runs=("batter_runs", "sum"),
        wickets=("wicket_count", "sum"),
        legal_balls=("is_legal", "sum"),
        dots=("is_dot", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum")
    )
)

bat_phase["run_rate"] = (
    bat_phase["runs"] /
    bat_phase["legal_balls"].replace(0, float("nan")) * 6
)

bat_phase.to_csv(
    OUTPUT / "phasewise/rr_batting_phasewise.csv",
    index=False
)

# ---------------------------------
# 6. RR BOWLING PHASE-WISE
# ---------------------------------

bowl_phase = (
    bowl.groupby(
        ["season", "match_id", "bowling_situation", "phase"],
        observed=True,
        as_index=False
    )
    .agg(
        runs_conceded=("total_runs", "sum"),
        bowler_runs=("bowler_runs", "sum"),
        wickets=("wicket_count", "sum"),
        bowler_wickets=("bowler_wicket", "sum"),
        legal_balls=("is_legal", "sum"),
        dots=("is_dot", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum")
    )
)

bowl_phase["economy"] = (
    bowl_phase["runs_conceded"] /
    bowl_phase["legal_balls"].replace(0, float("nan")) * 6
)

bowl_phase["bowler_economy"] = (
    bowl_phase["bowler_runs"] /
    bowl_phase["legal_balls"].replace(0, float("nan")) * 6
)

bowl_phase.to_csv(
    OUTPUT / "phasewise/rr_bowling_phasewise.csv",
    index=False
)

# ---------------------------------
# 7. VALIDATION AND OUTPUT
# ---------------------------------

print("\nAnalysis completed successfully!")

print("\nTotal matches:", df["match_id"].nunique())

print("\n--- OVER-WISE ---")
print("RR batting:", len(bat_over))
print("RR bowling:", len(bowl_over))

print("\n--- PHASE-WISE ---")
print("RR batting:", len(bat_phase))
print("RR bowling:", len(bowl_phase))

print("\n--- BATTING SITUATIONS ---")
print(bat_phase["batting_situation"].value_counts())

print("\n--- BOWLING SITUATIONS ---")
print(bowl_phase["bowling_situation"].value_counts())

print("\n--- SEASON-WISE MATCHES ---")
print(df.groupby("season")["match_id"].nunique())

print("\nAll CSV files saved in:", OUTPUT)
