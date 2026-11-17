
from pathlib import Path
import pandas as pd

RR = "Rajasthan Royals"

BASE = Path("data/processed")
OUT = BASE / "pressure_analysis"
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------
# 1. LOAD CORRECTED MATCH RESULTS
# ------------------------------------

matches = pd.read_csv(
    BASE / "rr_matches_2025_2026.csv",
    dtype={"match_id": str}
)

# Use final winner (including Super Over)
if "final_winner" not in matches.columns:
    matches["final_winner"] = matches["winner"]

# Ensure Delhi Capitals' Super Over victory is included
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

print("\n=== CORRECTED MATCH RESULTS ===")
print(matches.groupby(["season", "result"]).size())

# ------------------------------------
# 2. BATTING: WINS VS LOSSES
# ------------------------------------

bat = pd.read_csv(
    OUT / "rr_batter_pressure_overwise.csv",
    dtype={"match_id": str}
)

dismissals = pd.read_csv(
    OUT / "rr_batting_dismissals.csv",
    dtype={"match_id": str}
)

# Remove old result columns before merging
bat = bat.drop(
    columns=["result"],
    errors="ignore"
).merge(
    results,
    on="match_id",
    how="left",
    validate="many_to_one"
)

dismissals = dismissals.drop(
    columns=["result"],
    errors="ignore"
).merge(
    results,
    on="match_id",
    how="left",
    validate="many_to_one"
)

bat = bat[bat["result"].isin(["Win", "Loss"])].copy()

dismissals = dismissals[
    dismissals["result"].isin(["Win", "Loss"])
].copy()

# Count individual dismissals by phase
dismissal_counts = (
    dismissals.groupby(
        ["season", "result", "phase", "dismissed_player"],
        as_index=False,
        observed=True
    )
    .size()
    .rename(columns={
        "dismissed_player": "batter",
        "size": "dismissals"
    })
)

# Summarize batting performance
bat_summary = (
    bat.groupby(
        ["season", "result", "phase", "batter"],
        as_index=False,
        observed=True
    )
    .agg(
        matches=("match_id", "nunique"),
        runs=("runs", "sum"),
        balls=("balls", "sum")
    )
)

bat_summary = bat_summary.merge(
    dismissal_counts,
    on=["season", "result", "phase", "batter"],
    how="left"
)

bat_summary["dismissals"] = (
    bat_summary["dismissals"].fillna(0).astype(int)
)

bat_summary["strike_rate"] = (
    bat_summary["runs"] * 100 /
    bat_summary["balls"].replace(0, float("nan"))
).round(2)

bat_summary["runs_per_dismissal"] = (
    bat_summary["runs"] /
    bat_summary["dismissals"].replace(0, float("nan"))
).round(2)

bat_summary.to_csv(
    OUT / "batter_win_loss_comparison.csv",
    index=False
)

# ------------------------------------
# 3. BOWLING: WINS VS LOSSES
# ------------------------------------

bowl = pd.read_csv(
    OUT / "rr_bowler_pressure_overwise.csv",
    dtype={"match_id": str}
)

bowl = bowl.drop(
    columns=["result"],
    errors="ignore"
).merge(
    results,
    on="match_id",
    how="left",
    validate="many_to_one"
)

bowl = bowl[
    bowl["result"].isin(["Win", "Loss"])
].copy()

# Summarize bowling performance
bowl_summary = (
    bowl.groupby(
        ["season", "result", "situation", "phase", "bowler"],
        as_index=False,
        observed=True
    )
    .agg(
        matches=("match_id", "nunique"),
        runs=("runs", "sum"),
        balls=("balls", "sum"),
        wickets=("wickets", "sum")
    )
)

bowl_summary["economy"] = (
    bowl_summary["runs"] * 6 /
    bowl_summary["balls"].replace(0, float("nan"))
).round(2)

# Your weakness condition
bowl_summary["weakness"] = (
    bowl_summary["economy"] > 10
)

bowl_summary.to_csv(
    OUT / "bowler_win_loss_comparison.csv",
    index=False
)

# ------------------------------------
# 4. DISPLAY BATTING RESULTS
# ------------------------------------

print("\n=== BATTERS IN LOSSES (30+ BALLS) ===")

weak_batters = bat_summary[
    (bat_summary["result"] == "Loss") &
    (bat_summary["balls"] >= 30)
].sort_values("strike_rate")

print(
    weak_batters[
        [
            "season",
            "phase",
            "batter",
            "matches",
            "runs",
            "balls",
            "dismissals",
            "strike_rate"
        ]
    ].to_string(index=False)
)

# ------------------------------------
# 5. DISPLAY BOWLING RESULTS
# ------------------------------------

print("\n=== BOWLERS IN LOSSES (24+ LEGAL BALLS) ===")

weak_bowlers = bowl_summary[
    (bowl_summary["result"] == "Loss") &
    (bowl_summary["balls"] >= 24) &
    (bowl_summary["weakness"])
].sort_values(
    "economy",
    ascending=False
)

print(
    weak_bowlers[
        [
            "season",
            "situation",
            "phase",
            "bowler",
            "matches",
            "runs",
            "balls",
            "wickets",
            "economy"
        ]
    ].to_string(index=False)
)

# ------------------------------------
# 6. FINAL VALIDATION
# ------------------------------------

print("\n=== FINAL MATCH COUNT ===")
print("Total matches:", len(matches))
print("Wins:", (matches["result"] == "Win").sum())
print("Losses:", (matches["result"] == "Loss").sum())
print("Unknown:", (matches["result"] == "Unknown").sum())

print("\nReports saved to:", OUT)

