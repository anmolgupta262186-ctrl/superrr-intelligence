
import pandas as pd
from pathlib import Path

BASE = Path("data/processed")
OUT = BASE / "bowling_analysis"
OUT.mkdir(parents=True, exist_ok=True)

phase = pd.read_csv(BASE / "phasewise/rr_bowling_phasewise.csv")
overs = pd.read_csv(BASE / "overwise/rr_bowling_overwise.csv")

# 1. Phase-wise summary
phase_summary = (
    phase.groupby(
        ["season", "bowling_situation", "phase"],
        as_index=False
    )
    .agg(
        matches=("match_id", "nunique"),
        runs_conceded=("runs_conceded", "sum"),
        wickets=("wickets", "sum"),
        bowler_wickets=("bowler_wickets", "sum"),
        legal_balls=("legal_balls", "sum"),
        dots=("dots", "sum"),
        fours=("fours", "sum"),
        sixes=("sixes", "sum")
    )
)

phase_summary["economy"] = (
    phase_summary["runs_conceded"] /
    phase_summary["legal_balls"].replace(0, float("nan")) * 6
).round(2)

phase_summary["avg_runs_conceded"] = (
    phase_summary["runs_conceded"] /
    phase_summary["matches"]
).round(2)

phase_summary["avg_wickets"] = (
    phase_summary["wickets"] /
    phase_summary["matches"]
).round(2)

phase_summary.to_csv(
    OUT / "bowling_phase_summary.csv",
    index=False
)

# 2. Over-wise summary
over_summary = (
    overs.groupby(
        ["season", "bowling_situation", "over"],
        as_index=False
    )
    .agg(
        matches=("match_id", "nunique"),
        runs_conceded=("runs_conceded", "sum"),
        wickets=("wickets", "sum"),
        bowler_wickets=("bowler_wickets", "sum"),
        legal_balls=("legal_balls", "sum"),
        dots=("dots", "sum"),
        fours=("fours", "sum"),
        sixes=("sixes", "sum")
    )
)

over_summary["economy"] = (
    over_summary["runs_conceded"] /
    over_summary["legal_balls"].replace(0, float("nan")) * 6
).round(2)

over_summary["avg_runs_conceded"] = (
    over_summary["runs_conceded"] /
    over_summary["matches"]
).round(2)

over_summary["avg_wickets"] = (
    over_summary["wickets"] /
    over_summary["matches"]
).round(2)

over_summary.to_csv(
    OUT / "bowling_over_summary.csv",
    index=False
)

# 3. Worst match-specific bowling phases
worst_phases = phase.sort_values(
    ["economy", "wickets"],
    ascending=[False, True]
)

worst_phases.to_csv(
    OUT / "worst_bowling_phases.csv",
    index=False
)

# 4. Print results
print("\n=== PHASE-WISE BOWLING PERFORMANCE ===")
print(
    phase_summary[
        [
            "season", "bowling_situation", "phase",
            "matches", "avg_runs_conceded",
            "avg_wickets", "economy"
        ]
    ].to_string(index=False)
)

print("\n=== 10 MOST EXPENSIVE OVERS ===")
print(
    over_summary.sort_values(
        "avg_runs_conceded", ascending=False
    )[
        [
            "season", "bowling_situation", "over",
            "matches", "avg_runs_conceded",
            "avg_wickets", "economy"
        ]
    ].head(10).to_string(index=False)
)

print("\nSaved bowling analysis to:", OUT)
