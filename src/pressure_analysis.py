
from pathlib import Path
import pandas as pd

RR = "Rajasthan Royals"
BASE = Path("data/processed")
OUT = BASE / "pressure_analysis"
OUT.mkdir(parents=True, exist_ok=True)

balls = pd.read_csv(
    BASE / "rr_deliveries_2025_2026.csv",
    dtype={"match_id": str}
)

matches = pd.read_csv(
    BASE / "rr_matches_2025_2026.csv",
    dtype={"match_id": str}
)

# Exclude Super Overs
balls = balls[balls["innings"].isin([1, 2])].copy()

# Determine RR's match result
matches["result"] = matches["winner"].apply(
    lambda w: (
        "No Result" if pd.isna(w)
        else "Win" if w == RR
        else "Loss"
    )
)

# Match phases
def get_phase(over):
    if over <= 6:
        return "Powerplay"
    elif over <= 15:
        return "Middle"
    return "Death"

balls["phase"] = balls["over"].apply(get_phase)

# Legal deliveries
balls["legal_ball"] = ~balls["extras"].fillna("{}").str.contains(
    '"wides"|"noballs"',
    regex=True
)

# ---------------------------------
# 1. MATCH-WISE INNINGS TOTALS
# ---------------------------------

innings = (
    balls.groupby(["match_id", "innings"], as_index=False)
    .agg(
        innings_runs=("total_runs", "sum"),
        innings_wickets=("wicket_count", "sum"),
        legal_balls=("legal_ball", "sum")
    )
)

first_innings = innings[innings["innings"] == 1][
    ["match_id", "innings_runs"]
].rename(columns={
    "innings_runs": "first_innings_runs"
})

# Provisional target; revised DLS targets need separate handling
first_innings["estimated_target"] = (
    first_innings["first_innings_runs"] + 1
)

# ---------------------------------
# 2. MATCH + OVER-WISE DATA
# ---------------------------------

overwise = (
    balls.groupby(
        ["match_id", "season", "date", "innings",
         "batting_team", "bowling_team", "over", "phase"],
        as_index=False
    )
    .agg(
        runs=("total_runs", "sum"),
        wickets=("wicket_count", "sum"),
        legal_balls=("legal_ball", "sum")
    )
)

overwise = overwise.merge(
    matches[["match_id", "final_winner", "result"]],
    on="match_id",
    how="left"
)

overwise = overwise.merge(
    first_innings,
    on="match_id",
    how="left"
)

overwise = overwise.sort_values(
    ["match_id", "innings", "over"]
)

# Score at end of each over
overwise["cumulative_runs"] = (
    overwise.groupby(["match_id", "innings"])["runs"]
    .cumsum()
)

overwise["cumulative_wickets"] = (
    overwise.groupby(["match_id", "innings"])["wickets"]
    .cumsum()
)

overwise["cumulative_balls"] = (
    overwise.groupby(["match_id", "innings"])["legal_balls"]
    .cumsum()
)

# Remaining balls in a standard 20-over innings
overwise["balls_remaining"] = (
    120 - overwise["cumulative_balls"]
).clip(lower=0)

overwise["runs_remaining"] = (
    overwise["estimated_target"] -
    overwise["cumulative_runs"]
).clip(lower=0)

# Required rate after each over when chasing
overwise["required_run_rate"] = pd.NA

mask = (
    (overwise["innings"] == 2) &
    (overwise["balls_remaining"] > 0)
)

overwise.loc[mask, "required_run_rate"] = (
    overwise.loc[mask, "runs_remaining"] * 6 /
    overwise.loc[mask, "balls_remaining"]
).round(2)

overwise["rr_role"] = overwise.apply(
    lambda r: (
        "Batting - Setting Target"
        if r["batting_team"] == RR and r["innings"] == 1
        else "Batting - Chasing"
        if r["batting_team"] == RR
        else "Bowling - Bowling First"
        if r["innings"] == 1
        else "Bowling - Defending"
    ),
    axis=1
)

overwise.to_csv(
    OUT / "rr_match_overwise_context.csv",
    index=False
)

# ---------------------------------
# 3. PHASE-WISE MATCH PERFORMANCE
# ---------------------------------

phasewise = (
    overwise.groupby(
        ["match_id", "season", "result", "rr_role", "phase"],
        as_index=False
    )
    .agg(
        runs=("runs", "sum"),
        wickets=("wickets", "sum"),
        legal_balls=("legal_balls", "sum")
    )
)

phasewise["run_rate"] = (
    phasewise["runs"] * 6 /
    phasewise["legal_balls"].replace(0, float("nan"))
).round(2)

phasewise["bowling_weakness"] = (
    phasewise["rr_role"].str.startswith("Bowling") &
    (phasewise["run_rate"] > 10)
)

phasewise.to_csv(
    OUT / "rr_match_phasewise_context.csv",
    index=False
)

# ---------------------------------
# 4. COMPARE WINS AND LOSSES
# ---------------------------------

comparison = (
    phasewise.groupby(
        ["season", "result", "rr_role", "phase"],
        as_index=False
    )
    .agg(
        matches=("match_id", "nunique"),
        runs=("runs", "sum"),
        wickets=("wickets", "sum"),
        legal_balls=("legal_balls", "sum")
    )
)

comparison["run_rate"] = (
    comparison["runs"] * 6 /
    comparison["legal_balls"].replace(0, float("nan"))
).round(2)

comparison["wickets_per_match"] = (
    comparison["wickets"] /
    comparison["matches"]
).round(2)

comparison.to_csv(
    OUT / "rr_wins_vs_losses.csv",
    index=False
)

# ---------------------------------
# 5. FLAG MATCH-SPECIFIC WEAKNESSES
# ---------------------------------

weak_bowling = phasewise[
    phasewise["bowling_weakness"]
].sort_values("run_rate", ascending=False)

weak_bowling.to_csv(
    OUT / "rr_expensive_bowling_phases.csv",
    index=False
)

# ---------------------------------
# 6. PRINT SUMMARY
# ---------------------------------

print("\n=== MATCH RESULTS ===")
print(matches.groupby(["season", "result"]).size())

print("\n=== WINS VS LOSSES ===")
print(
    comparison[
        ["season", "result", "rr_role", "phase",
         "matches", "run_rate", "wickets_per_match"]
    ].to_string(index=False)
)

print("\n=== MOST EXPENSIVE BOWLING PHASES ===")
print(
    weak_bowling[
        ["match_id", "season", "result", "rr_role",
         "phase", "runs", "wickets", "run_rate"]
    ].head(10).to_string(index=False)
)

print("\nFiles saved to:", OUT)
