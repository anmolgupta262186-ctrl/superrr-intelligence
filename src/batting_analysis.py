
import pandas as pd
from pathlib import Path

BASE = Path("data/processed")
OUT = BASE / "batting_analysis"
OUT.mkdir(parents=True, exist_ok=True)

phase = pd.read_csv(BASE / "phasewise/rr_batting_phasewise.csv")
overs = pd.read_csv(BASE / "overwise/rr_batting_overwise.csv")

# ---------------------------------
# 1. PHASE-WISE PERFORMANCE
# ---------------------------------

phase_summary = (
    phase.groupby(
        ["season", "batting_situation", "phase"],
        as_index=False
    )
    .agg(
        matches=("match_id", "nunique"),
        runs=("runs", "sum"),
        wickets=("wickets", "sum"),
        legal_balls=("legal_balls", "sum"),
        dots=("dots", "sum"),
        fours=("fours", "sum"),
        sixes=("sixes", "sum")
    )
)

phase_summary["run_rate"] = (
    phase_summary["runs"] /
    phase_summary["legal_balls"] * 6
).round(2)

phase_summary["avg_runs"] = (
    phase_summary["runs"] / phase_summary["matches"]
).round(2)

phase_summary["avg_wickets"] = (
    phase_summary["wickets"] / phase_summary["matches"]
).round(2)

phase_summary["dot_percentage"] = (
    phase_summary["dots"] /
    phase_summary["legal_balls"] * 100
).round(2)

phase_summary.to_csv(
    OUT / "batting_phase_summary.csv",
    index=False
)

# ---------------------------------
# 2. OVER-WISE PERFORMANCE
# ---------------------------------

over_summary = (
    overs.groupby(
        ["season", "batting_situation", "over"],
        as_index=False
    )
    .agg(
        matches=("match_id", "nunique"),
        runs=("runs", "sum"),
        wickets=("wickets", "sum"),
        legal_balls=("legal_balls", "sum"),
        dots=("dots", "sum"),
        fours=("fours", "sum"),
        sixes=("sixes", "sum")
    )
)

over_summary["run_rate"] = (
    over_summary["runs"] /
    over_summary["legal_balls"] * 6
).round(2)

over_summary["avg_runs"] = (
    over_summary["runs"] / over_summary["matches"]
).round(2)

over_summary["avg_wickets"] = (
    over_summary["wickets"] / over_summary["matches"]
).round(2)

over_summary.to_csv(
    OUT / "batting_over_summary.csv",
    index=False
)

# ---------------------------------
# 3. WORST INDIVIDUAL PHASES
# ---------------------------------

worst_phases = phase.sort_values(
    ["run_rate", "wickets"],
    ascending=[True, False]
)

worst_phases.to_csv(
    OUT / "worst_batting_phases.csv",
    index=False
)

# ---------------------------------
# 4. DISPLAY RESULTS
# ---------------------------------

print("\n=== PHASE-WISE BATTING PERFORMANCE ===")
print(
    phase_summary[
        [
            "season", "batting_situation", "phase",
            "matches", "avg_runs", "avg_wickets",
            "run_rate", "dot_percentage"
        ]
    ].to_string(index=False)
)

print("\n=== 10 LOWEST-SCORING OVERS ===")
print(
    over_summary.sort_values("avg_runs")
    [
        [
            "season", "batting_situation", "over",
            "matches", "avg_runs", "avg_wickets"
        ]
    ].head(10).to_string(index=False)
)

print("\nSaved analysis files to:", OUT)
