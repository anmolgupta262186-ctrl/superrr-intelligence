
import json
from pathlib import Path

import pandas as pd

RR = "Rajasthan Royals"
BASE = Path("data/processed")
OUT = BASE / "player_analysis"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    BASE / "rr_deliveries_2025_2026.csv",
    dtype={"match_id": str}
)

df = df[df["innings"].isin([1, 2])].copy()

df["phase"] = pd.cut(
    df["over"],
    bins=[0, 6, 15, 20],
    labels=["Powerplay", "Middle", "Death"]
)

df["extras_data"] = df["extras"].fillna("{}").apply(json.loads)

df["legal_ball"] = df["extras_data"].apply(
    lambda x: int("wides" not in x and "noballs" not in x)
)

df["batter_ball"] = df["extras_data"].apply(
    lambda x: int("wides" not in x)
)

df["bowler_runs"] = df.apply(
    lambda r: r["total_runs"]
    - r["extras_data"].get("byes", 0)
    - r["extras_data"].get("legbyes", 0)
    - r["extras_data"].get("penalty", 0),
    axis=1
)

df["four"] = (df["batter_runs"] == 4).astype(int)
df["six"] = (df["batter_runs"] == 6).astype(int)

df["bowler_dot"] = (df["bowler_runs"] == 0).astype(int)

BOWLER_WICKETS = {
    "bowled", "caught", "caught and bowled",
    "lbw", "stumped", "hit wicket"
}

df["bowler_wickets"] = df["dismissal_types"].fillna("").apply(
    lambda s: sum(
        kind.strip() in BOWLER_WICKETS
        for kind in s.split(",") if kind
    )
)

# ---------------------------------
# 1. DETERMINE BATTING POSITION
# ---------------------------------

positions = []

for (match_id, innings), group in df.groupby(
    ["match_id", "innings"], sort=False
):
    group = group.sort_index()

    order = []

    for _, ball in group.iterrows():
        for player in [ball["batter"], ball["non_striker"]]:
            if player not in order:
                order.append(player)

    for pos, player in enumerate(order, start=1):
        positions.append({
            "match_id": match_id,
            "innings": innings,
            "batter": player,
            "batting_position": pos
        })

positions = pd.DataFrame(positions)

# Opening pair positions 1 and 2 depend on who faced first.
# This identifies batting order, not an official scorecard order.

df = df.merge(
    positions,
    on=["match_id", "innings", "batter"],
    how="left"
)

# ---------------------------------
# 2. RR BATTER PERFORMANCE BY PHASE
# ---------------------------------

bat = df[df["batting_team"] == RR].copy()

bat["situation"] = bat["innings"].map({
    1: "Setting Target",
    2: "Chasing"
})

bat_summary = (
    bat.groupby(
        ["season", "situation", "phase", "batter"],
        observed=True,
        as_index=False
    )
    .agg(
        innings=("match_id", "nunique"),
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum"),
        fours=("four", "sum"),
        sixes=("six", "sum")
    )
)

bat_summary["strike_rate"] = (
    100 * bat_summary["runs"] /
    bat_summary["balls"].replace(0, float("nan"))
).round(2)

bat_summary["boundary_percentage"] = (
    100 * (bat_summary["fours"] + bat_summary["sixes"]) /
    bat_summary["balls"].replace(0, float("nan"))
).round(2)

bat_summary["low_strike_rate"] = (
    (bat_summary["strike_rate"] < 120) &
    (bat_summary["balls"] >= 30)
)

bat_summary.to_csv(
    OUT / "rr_batters_by_phase.csv", index=False
)

# ---------------------------------
# 3. BATTING POSITION ANALYSIS
# ---------------------------------

position_summary = (
    bat.groupby(
        ["season", "batting_position"],
        as_index=False
    )
    .agg(
        innings=("match_id", "nunique"),
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum")
    )
)

position_summary["strike_rate"] = (
    100 * position_summary["runs"] /
    position_summary["balls"].replace(0, float("nan"))
).round(2)

position_summary["avg_runs"] = (
    position_summary["runs"] /
    position_summary["innings"]
).round(2)

position_summary.to_csv(
    OUT / "rr_batting_positions.csv", index=False
)

# ---------------------------------
# 4. RR BOWLER PERFORMANCE BY PHASE
# ---------------------------------

bowl = df[df["bowling_team"] == RR].copy()

bowl["situation"] = bowl["innings"].map({
    1: "Bowling First",
    2: "Defending"
})

bowl_summary = (
    bowl.groupby(
        ["season", "situation", "phase", "bowler"],
        observed=True,
        as_index=False
    )
    .agg(
        matches=("match_id", "nunique"),
        runs_conceded=("bowler_runs", "sum"),
        balls=("legal_ball", "sum"),
        wickets=("bowler_wickets", "sum"),
        dots=("bowler_dot", "sum"),
        fours=("four", "sum"),
        sixes=("six", "sum")
    )
)

bowl_summary["economy"] = (
    6 * bowl_summary["runs_conceded"] /
    bowl_summary["balls"].replace(0, float("nan"))
).round(2)

bowl_summary["weakness"] = (
    bowl_summary["economy"] > 10
)

bowl_summary.to_csv(
    OUT / "rr_bowlers_by_phase.csv", index=False
)

# ---------------------------------
# 5. DISPLAY BATTING WEAKNESSES
# ---------------------------------

print("\n=== RR BATTERS: LOW STRIKE RATE BY PHASE ===")

weak_batters = bat_summary[
    bat_summary["low_strike_rate"]
].sort_values("strike_rate")

print(
    weak_batters[
        ["season", "situation", "phase", "batter",
         "runs", "balls", "strike_rate"]
    ].to_string(index=False)
)

print("\n=== BATTING POSITIONS ===")

print(
    position_summary[
        ["season", "batting_position", "innings",
         "avg_runs", "strike_rate"]
    ].to_string(index=False)
)

# ---------------------------------
# 6. DISPLAY BOWLING WEAKNESSES
# ---------------------------------

print("\n=== RR BOWLERS WITH ECONOMY ABOVE 10 ===")

weak_bowlers = bowl_summary[
    bowl_summary["weakness"]
].sort_values("economy", ascending=False)

print(
    weak_bowlers[
        ["season", "situation", "phase", "bowler",
         "matches", "balls", "runs_conceded",
         "wickets", "economy"]
    ].to_string(index=False)
)

print("\nFiles saved to:", OUT)
