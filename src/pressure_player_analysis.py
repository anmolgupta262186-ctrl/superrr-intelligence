
import json
from pathlib import Path

import pandas as pd

RR = "Rajasthan Royals"
BASE = Path("data/processed")
OUT = BASE / "pressure_analysis"

OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD DATA
# ------------------------------------

df = pd.read_csv(
    BASE / "rr_deliveries_2025_2026.csv",
    dtype={"match_id": str}
)

matches = pd.read_csv(
    BASE / "rr_matches_2025_2026.csv",
    dtype={"match_id": str}
)

# Use corrected final winner, including Super Overs
if "final_winner" not in matches.columns:
    matches["final_winner"] = matches["winner"]

# Correct DC vs RR Super Over result
matches.loc[
    matches["match_id"] == "1473469",
    "final_winner"
] = "Delhi Capitals"

matches["result"] = matches["final_winner"].apply(
    lambda w: (
        "Unknown" if pd.isna(w)
        else "Win" if w == RR
        else "Loss"
    )
)

results = matches[["match_id", "result"]]

# Exclude Super Over deliveries from regular phase analysis
df = df[df["innings"].isin([1, 2])].copy()

df = df.merge(
    results,
    on="match_id",
    how="left",
    validate="many_to_one"
)

# ------------------------------------
# 2. PREPROCESS DELIVERIES
# ------------------------------------

df["phase"] = pd.cut(
    df["over"],
    bins=[0, 6, 15, 20],
    labels=["Powerplay", "Middle", "Death"]
)

df["extras_data"] = (
    df["extras"].fillna("{}").apply(json.loads)
)

# Legal balls exclude wides and no-balls
df["legal"] = df["extras_data"].apply(
    lambda x: int(
        "wides" not in x and "noballs" not in x
    )
)

# A batter faces a ball even when it is a no-ball
# but does not face a delivery recorded as a wide
df["batter_ball"] = df["extras_data"].apply(
    lambda x: int("wides" not in x)
)

# Runs charged to an individual bowler
df["bowler_runs"] = df.apply(
    lambda r: (
        r["total_runs"]
        - r["extras_data"].get("byes", 0)
        - r["extras_data"].get("legbyes", 0)
        - r["extras_data"].get("penalty", 0)
    ),
    axis=1
)

BOWLER_DISMISSALS = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket"
}

df["bowler_wickets"] = (
    df["dismissal_types"]
    .fillna("")
    .apply(
        lambda s: sum(
            kind.strip() in BOWLER_DISMISSALS
            for kind in s.split(",")
            if kind.strip()
        )
    )
)

# ------------------------------------
# 3. RR BOWLING ANALYSIS
# ------------------------------------

bowling = df[df["bowling_team"] == RR].copy()

bowling["situation"] = bowling["innings"].map({
    1: "Bowling First",
    2: "Defending"
})

# Bowler-wise performance in every over
bowler_overs = (
    bowling.groupby(
        [
            "season",
            "match_id",
            "result",
            "situation",
            "phase",
            "over",
            "bowler"
        ],
        observed=True,
        as_index=False
    )
    .agg(
        runs=("bowler_runs", "sum"),
        balls=("legal", "sum"),
        wickets=("bowler_wickets", "sum")
    )
)

bowler_overs["economy"] = (
    6 * bowler_overs["runs"]
    / bowler_overs["balls"].replace(0, float("nan"))
).round(2)

# User-defined weakness threshold
bowler_overs["above_10"] = (
    bowler_overs["economy"] > 10
)

bowler_overs.to_csv(
    OUT / "rr_bowler_pressure_overwise.csv",
    index=False
)

# ------------------------------------
# 4. RR BATTING ANALYSIS
# ------------------------------------

batting = df[df["batting_team"] == RR].copy()

batting["situation"] = batting["innings"].map({
    1: "Setting Target",
    2: "Chasing"
})

batter_overs = (
    batting.groupby(
        [
            "season",
            "match_id",
            "result",
            "situation",
            "phase",
            "over",
            "batter"
        ],
        observed=True,
        as_index=False
    )
    .agg(
        runs=("batter_runs", "sum"),
        balls=("batter_ball", "sum")
    )
)

batter_overs["strike_rate"] = (
    100 * batter_overs["runs"]
    / batter_overs["balls"].replace(0, float("nan"))
).round(2)

batter_overs.to_csv(
    OUT / "rr_batter_pressure_overwise.csv",
    index=False
)

# ------------------------------------
# 5. RR BATTING DISMISSALS
# ------------------------------------

dismissals = batting[
    batting["players_out"].notna()
].copy()

dismissals = dismissals.assign(
    dismissed_player=(
        dismissals["players_out"].str.split(",")
    )
).explode("dismissed_player")

dismissals["dismissed_player"] = (
    dismissals["dismissed_player"].str.strip()
)

dismissals = dismissals[
    dismissals["dismissed_player"].notna()
    & (dismissals["dismissed_player"] != "")
].copy()

dismissals[
    [
        "season",
        "match_id",
        "result",
        "situation",
        "phase",
        "over",
        "dismissed_player",
        "bowler",
        "dismissal_types"
    ]
].to_csv(
    OUT / "rr_batting_dismissals.csv",
    index=False
)

# ------------------------------------
# 6. EXPENSIVE BOWLING SPELLS
# ------------------------------------

bowler_phases = (
    bowler_overs.groupby(
        [
            "season",
            "match_id",
            "result",
            "situation",
            "phase",
            "bowler"
        ],
        observed=True,
        as_index=False
    )
    .agg(
        runs=("runs", "sum"),
        balls=("balls", "sum"),
        wickets=("wickets", "sum")
    )
)

bowler_phases["economy"] = (
    6 * bowler_phases["runs"]
    / bowler_phases["balls"].replace(0, float("nan"))
).round(2)

weak_bowlers = bowler_phases[
    (bowler_phases["result"] == "Loss")
    & (bowler_phases["economy"] > 10)
    & (bowler_phases["balls"] >= 12)
].sort_values(
    "economy",
    ascending=False
)

print("\n=== EXPENSIVE BOWLING SPELLS IN LOSSES ===")

print(
    weak_bowlers.head(20).to_string(index=False)
)

# ------------------------------------
# 7. WICKETS LOST IN LOSSES
# ------------------------------------

print("\n=== RR WICKETS LOST IN LOSSES ===")

wicket_summary = (
    dismissals[dismissals["result"] == "Loss"]
    .groupby(
        ["season", "phase", "dismissed_player"],
        observed=True
    )
    .size()
    .sort_values(ascending=False)
)

print(wicket_summary.head(20))

# ------------------------------------
# 8. VALIDATION
# ------------------------------------

print("\n=== CORRECTED MATCH RESULTS ===")
print(matches.groupby(["season", "result"]).size())

print("\nTotal matches:", len(matches))

print(
    "RR wins:",
    (matches["result"] == "Win").sum()
)

print(
    "RR losses:",
    (matches["result"] == "Loss").sum()
)

print(
    "Unknown results:",
    (matches["result"] == "Unknown").sum()
)

print("\nReports saved to:", OUT)
